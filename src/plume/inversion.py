"""
Plume Inversion Module.

Given an observed concentration map (from high-res satellite),
optimizes the Gaussian plume model parameters to estimate the
emission rate Q (kg/hr) and source location.
"""

import torch
import torch.nn as nn
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

from src.plume.gaussian_plume import GaussianPlumeModel, PG_COEFFICIENTS


@dataclass
class InversionResult:
    """Result of plume inversion optimization."""
    estimated_Q_kg_hr: float       # Estimated emission rate
    estimated_Q_kg_s: float
    estimated_source_x: float      # Estimated source position (m)
    estimated_source_y: float
    true_Q_kg_hr: Optional[float]  # True rate (if known, for validation)
    error_pct: Optional[float]     # Percentage error vs true
    confidence_interval: Tuple[float, float]  # 95% CI on Q (kg/hr)
    final_loss: float
    n_iterations: int
    converged: bool


class PlumeInverter:
    """
    Inverse optimization for methane emission rates.
    
    Takes an observed concentration map and wind data,
    then optimizes the Gaussian plume model to find Q (emission rate)
    and source location that best fit the observations.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        max_iterations: int = 2000,
        convergence_tol: float = 1e-6,
        min_iterations: int = 300,
        stability_class: str = "D",
    ):
        self.lr = learning_rate
        self.max_iter = max_iterations
        self.tol = convergence_tol
        self.min_iter = min_iterations
        self.stability_class = stability_class

    def invert(
        self,
        observed_concentrations: np.ndarray,
        receptor_x: np.ndarray,
        receptor_y: np.ndarray,
        receptor_z: np.ndarray,
        wind_speed: float = 3.0,
        initial_Q: float = 0.01,    # kg/s initial guess
        source_height: float = 5.0,
        true_Q_kg_hr: Optional[float] = None,
    ) -> InversionResult:
        """
        Run inverse optimization to estimate emission rate.
        
        Args:
            observed_concentrations: 1D array of observed C at receptor locations
            receptor_x, _y, _z: 1D arrays of receptor positions (m)
            wind_speed: wind speed (m/s)
            initial_Q: initial guess for emission rate (kg/s)
            source_height: source height (m)
            true_Q_kg_hr: true emission rate for validation (optional)
        
        Returns:
            InversionResult with estimated emission rate and diagnostics
        """
        # Convert to tensors
        obs_raw = torch.tensor(observed_concentrations, dtype=torch.float64)
        rx = torch.tensor(receptor_x, dtype=torch.float64)
        ry = torch.tensor(receptor_y, dtype=torch.float64)
        rz = torch.tensor(receptor_z, dtype=torch.float64)

        # ── Scale observations to avoid vanishing gradients ──
        # When wind is strong or Q is small, concentrations can be ~1e-10,
        # making MSE loss ~1e-20 with near-zero gradients.
        obs_scale = obs_raw.max().item()
        if obs_scale < 1e-15:
            obs_scale = 1.0  # fallback if all zeros
        obs = obs_raw / obs_scale

        # ── Adaptive initial Q ──
        # Estimate Q₀ from the peak observed concentration:
        #   C_peak ≈ Q / (2π u σ_y σ_z)  at the receptor with highest C
        # This gives a much better starting point than a fixed 0.01.
        adaptive_Q = self._estimate_initial_Q(
            observed_concentrations, receptor_x, wind_speed, source_height
        )
        if adaptive_Q is not None and adaptive_Q > 1e-10:
            initial_Q = adaptive_Q

        # Initialize model
        model = GaussianPlumeModel(
            emission_rate=initial_Q,
            source_x=0.0,
            source_y=0.0,
            source_height=source_height,
            stability_class=self.stability_class,
        )

        # Use Adam with a learning-rate scheduler
        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=100, min_lr=1e-5
        )
        loss_fn = nn.MSELoss()

        prev_loss = float("inf")
        converged = False
        final_loss = 0.0

        for i in range(self.max_iter):
            optimizer.zero_grad()

            predicted_raw = model.forward(rx, ry, rz, wind_speed)
            predicted = predicted_raw / obs_scale   # same scaling
            loss = loss_fn(predicted, obs)

            loss.backward()
            optimizer.step()
            scheduler.step(loss)

            current_loss = loss.item()

            # Only check convergence after warm-up iterations
            if i >= self.min_iter:
                # Relative convergence criterion
                rel_change = abs(prev_loss - current_loss) / (abs(prev_loss) + 1e-30)
                if rel_change < self.tol:
                    converged = True
                    final_loss = current_loss
                    break

            prev_loss = current_loss
            final_loss = current_loss

        # Compute confidence interval via Hessian approximation
        ci_low, ci_high = self._compute_confidence_interval(model, obs, rx, ry, rz, wind_speed)

        estimated_Q_kg_hr = model.Q_kg_hr
        estimated_Q_kg_s = model.Q.item()

        # Error vs true value
        error_pct = None
        if true_Q_kg_hr is not None and true_Q_kg_hr > 0:
            error_pct = round(
                100 * abs(estimated_Q_kg_hr - true_Q_kg_hr) / true_Q_kg_hr, 2
            )

        return InversionResult(
            estimated_Q_kg_hr=round(estimated_Q_kg_hr, 4),
            estimated_Q_kg_s=round(estimated_Q_kg_s, 8),
            estimated_source_x=round(model.src_x.item(), 2),
            estimated_source_y=round(model.src_y.item(), 2),
            true_Q_kg_hr=true_Q_kg_hr,
            error_pct=error_pct,
            confidence_interval=(round(ci_low, 4), round(ci_high, 4)),
            final_loss=round(final_loss, 12),
            n_iterations=i + 1,
            converged=converged,
        )

    def _estimate_initial_Q(
        self, observed_concentrations, receptor_x, wind_speed, source_height
    ) -> Optional[float]:
        """
        Estimate a reasonable initial Q (kg/s) from observed concentrations.

        Uses the peak-concentration receptor and the analytic Gaussian formula
        to back-calculate an approximate emission rate.
        """
        try:
            peak_idx = int(np.argmax(observed_concentrations))
            C_peak = observed_concentrations[peak_idx]
            if C_peak <= 0:
                return None

            x_peak = max(float(receptor_x[peak_idx]), 10.0)
            u = max(wind_speed, 0.5)

            coeff = PG_COEFFICIENTS.get(self.stability_class, PG_COEFFICIENTS["D"])
            x_km = x_peak / 1000.0
            sy = coeff["a"] * (x_km ** coeff["b"]) * 1000  # metres
            sz = coeff["c"] * (x_km ** coeff["d"]) * 1000

            # C_peak ≈ Q / (2π u σ_y σ_z)  (on centreline, ground-level source)
            Q_est = C_peak * 2 * np.pi * u * sy * sz
            return float(np.clip(Q_est, 1e-10, 100.0))
        except Exception:
            return None

    def _compute_confidence_interval(
        self, model, obs, rx, ry, rz, wind_speed, alpha=0.05
    ) -> Tuple[float, float]:
        """
        Compute approximate 95% confidence interval for Q
        using the Hessian of the loss w.r.t. log(Q).
        Clamped to avoid overflow in exp().
        """
        try:
            model.zero_grad()
            predicted = model.forward(rx, ry, rz, wind_speed)
            loss = nn.MSELoss()(predicted, obs)

            # Compute second derivative of loss w.r.t. log(Q)
            grad = torch.autograd.grad(loss, model.log_Q, create_graph=True)[0]
            hessian = torch.autograd.grad(grad, model.log_Q)[0]

            if hessian.item() > 0:
                se_log_Q = 1.0 / np.sqrt(hessian.item())
                # Clamp se to prevent overflow: exp(700) ≈ inf for float64
                se_log_Q = min(se_log_Q, 50.0)
                z = 1.96  # 95% CI

                log_Q = model.log_Q.item()
                ci_low = np.exp(np.clip(log_Q - z * se_log_Q, -50, 50)) * 3600
                ci_high = np.exp(np.clip(log_Q + z * se_log_Q, -50, 50)) * 3600
                return ci_low, ci_high
        except Exception:
            pass

        # Fallback: ±30% of estimate
        Q = model.Q_kg_hr
        return Q * 0.7, Q * 1.3

    def create_synthetic_observation(
        self,
        true_Q_kg_s: float = 0.014,    # ~50 kg/hr
        wind_speed: float = 3.0,
        source_height: float = 5.0,
        stability_class: str = "D",
        n_receptors: int = 200,
        domain_m: float = 3000,
        noise_level: float = 0.05,     # 5% Gaussian noise
    ) -> dict:
        """
        Create a synthetic observation for testing the inversion.
        
        Returns dict with receptor positions, observed concentrations,
        and true parameters for validation.
        """
        # Use a seed derived from the input parameters so each emission
        # rate + wind combination gets a unique (but reproducible) receptor layout.
        seed = int(abs(true_Q_kg_s * 1e6 + wind_speed * 1e3 + source_height * 10)) % (2**31)
        rng = np.random.RandomState(seed)

        # Ground truth model
        true_model = GaussianPlumeModel(
            emission_rate=true_Q_kg_s,
            source_x=0.0,
            source_y=0.0,
            source_height=source_height,
            stability_class=stability_class,
        )

        # Generate receptor positions (downwind, spread out)
        rx = rng.uniform(100, domain_m, n_receptors)
        ry = rng.uniform(-domain_m / 3, domain_m / 3, n_receptors)
        rz = np.zeros(n_receptors)  # Ground level

        rx_t = torch.tensor(rx, dtype=torch.float64)
        ry_t = torch.tensor(ry, dtype=torch.float64)
        rz_t = torch.tensor(rz, dtype=torch.float64)

        with torch.no_grad():
            true_conc = true_model.forward(rx_t, ry_t, rz_t, wind_speed).numpy()

        # Add noise
        noise = rng.normal(0, noise_level * np.max(true_conc), size=true_conc.shape)
        observed = np.maximum(true_conc + noise, 0)

        return {
            "receptor_x": rx,
            "receptor_y": ry,
            "receptor_z": rz,
            "observed_concentrations": observed,
            "true_concentrations": true_conc,
            "true_Q_kg_s": true_Q_kg_s,
            "true_Q_kg_hr": true_Q_kg_s * 3600,
            "wind_speed": wind_speed,
            "source_height": source_height,
            "stability_class": stability_class,
        }
