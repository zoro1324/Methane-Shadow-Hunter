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
        learning_rate: float = 0.01,
        max_iterations: int = 1000,
        convergence_tol: float = 1e-8,
        stability_class: str = "D",
    ):
        self.lr = learning_rate
        self.max_iter = max_iterations
        self.tol = convergence_tol
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
        obs = torch.tensor(observed_concentrations, dtype=torch.float64)
        rx = torch.tensor(receptor_x, dtype=torch.float64)
        ry = torch.tensor(receptor_y, dtype=torch.float64)
        rz = torch.tensor(receptor_z, dtype=torch.float64)

        # Initialize model with initial guess
        model = GaussianPlumeModel(
            emission_rate=initial_Q,
            source_x=0.0,
            source_y=0.0,
            source_height=source_height,
            stability_class=self.stability_class,
        )

        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr)
        loss_fn = nn.MSELoss()

        prev_loss = float("inf")
        converged = False
        final_loss = 0.0

        for i in range(self.max_iter):
            optimizer.zero_grad()

            predicted = model.forward(rx, ry, rz, wind_speed)
            loss = loss_fn(predicted, obs)

            loss.backward()
            optimizer.step()

            current_loss = loss.item()

            if abs(prev_loss - current_loss) < self.tol:
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

    def _compute_confidence_interval(
        self, model, obs, rx, ry, rz, wind_speed, alpha=0.05
    ) -> Tuple[float, float]:
        """
        Compute approximate 95% confidence interval for Q
        using the Hessian of the loss w.r.t. log(Q).
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
                z = 1.96  # 95% CI

                log_Q = model.log_Q.item()
                ci_low = np.exp(log_Q - z * se_log_Q) * 3600
                ci_high = np.exp(log_Q + z * se_log_Q) * 3600
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
        rng = np.random.RandomState(42)

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
