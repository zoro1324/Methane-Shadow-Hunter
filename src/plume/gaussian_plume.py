"""
Gaussian Plume Forward Model (PyTorch).

Differentiable implementation of the Gaussian plume dispersion equation
for atmospheric methane concentration modeling.

The Gaussian plume formula:
    C(x,y,z) = Q / (2π u σ_y σ_z) × exp(-y²/(2σ_y²)) 
               × [exp(-(z-H)²/(2σ_z²)) + exp(-(z+H)²/(2σ_z²))]

Where:
    Q = emission rate (kg/s)
    u = wind speed (m/s)
    σ_y, σ_z = dispersion coefficients (m) as functions of downwind distance x
    H = effective source height (m)
"""

import torch
import torch.nn as nn
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple


# Pasquill-Gifford stability class coefficients
# σ_y(x) = a * x^b,  σ_z(x) = c * x^d  (x in km, σ in m)
PG_COEFFICIENTS = {
    "A": {"a": 0.22, "b": 0.894, "c": 0.20, "d": 0.894},   # Very unstable
    "B": {"a": 0.16, "b": 0.894, "c": 0.12, "d": 0.894},   # Unstable
    "C": {"a": 0.11, "b": 0.894, "c": 0.08, "d": 0.894},   # Slightly unstable
    "D": {"a": 0.08, "b": 0.894, "c": 0.06, "d": 0.894},   # Neutral
    "E": {"a": 0.06, "b": 0.894, "c": 0.03, "d": 0.894},   # Slightly stable
    "F": {"a": 0.04, "b": 0.894, "c": 0.016, "d": 0.894},  # Stable
}


@dataclass
class PlumeParams:
    """Parameters for the Gaussian plume model."""
    emission_rate_kg_s: float     # Q (kg/s)
    source_x: float               # Source x position (m)
    source_y: float               # Source y position (m)
    source_height: float          # H (m), effective stack/vent height
    wind_speed: float             # u (m/s)
    wind_direction_deg: float     # Wind direction in degrees from north
    stability_class: str          # Pasquill-Gifford class A-F


class GaussianPlumeModel(nn.Module):
    """
    Differentiable Gaussian Plume Model in PyTorch.
    
    Can be used in:
    1. Forward mode: given Q, compute concentration field
    2. Inverse mode: given concentrations, optimize Q
    """

    def __init__(
        self,
        emission_rate: float = 0.01,     # kg/s (initial guess)
        source_x: float = 0.0,          # m
        source_y: float = 0.0,          # m
        source_height: float = 5.0,     # m (ground-level source like a valve)
        stability_class: str = "D",     # Neutral stability
    ):
        super().__init__()

        # Learnable parameters (for inverse optimization)
        self.log_Q = nn.Parameter(torch.tensor(np.log(max(emission_rate, 1e-8)), dtype=torch.float64))
        self.src_x = nn.Parameter(torch.tensor(source_x, dtype=torch.float64))
        self.src_y = nn.Parameter(torch.tensor(source_y, dtype=torch.float64))

        # Fixed parameters
        self.H = source_height
        self.stability_class = stability_class
        self._set_pg_coefficients(stability_class)

    def _set_pg_coefficients(self, cls: str):
        """Set Pasquill-Gifford dispersion coefficients."""
        coeff = PG_COEFFICIENTS.get(cls, PG_COEFFICIENTS["D"])
        self.pg_a = coeff["a"]
        self.pg_b = coeff["b"]
        self.pg_c = coeff["c"]
        self.pg_d = coeff["d"]

    @property
    def Q(self) -> torch.Tensor:
        """Emission rate in kg/s (always positive via exp)."""
        return torch.exp(self.log_Q)

    @property
    def Q_kg_hr(self) -> float:
        """Emission rate in kg/hr."""
        return float(self.Q.item() * 3600)

    def sigma_y(self, x_km: torch.Tensor) -> torch.Tensor:
        """Lateral dispersion coefficient σ_y (m) as function of downwind distance (km)."""
        x_km = torch.clamp(x_km, min=0.01)
        return self.pg_a * x_km ** self.pg_b * 1000  # Convert to meters

    def sigma_z(self, x_km: torch.Tensor) -> torch.Tensor:
        """Vertical dispersion coefficient σ_z (m) as function of downwind distance (km)."""
        x_km = torch.clamp(x_km, min=0.01)
        return self.pg_c * x_km ** self.pg_d * 1000  # Convert to meters

    def forward(
        self,
        receptor_x: torch.Tensor,   # receptor x positions (m)
        receptor_y: torch.Tensor,   # receptor y positions (m)
        receptor_z: torch.Tensor,   # receptor z positions (m), typically 0 (ground)
        wind_speed: float = 3.0,    # m/s
    ) -> torch.Tensor:
        """
        Compute concentration at receptor locations.
        
        All positions in meters, relative to wind-aligned coordinate system.
        x = downwind direction, y = crosswind, z = vertical.
        
        Returns: concentration in kg/m³
        """
        Q = self.Q
        u = max(wind_speed, 0.5)  # Minimum wind speed
        H = self.H

        # Downwind distance from source
        dx = receptor_x - self.src_x
        dy = receptor_y - self.src_y
        dz = receptor_z

        # Convert downwind distance to km for sigma functions
        dx_km = dx / 1000.0

        # Only compute for downwind locations (x > source)
        # Use a soft mask to keep differentiability
        downwind_mask = torch.sigmoid(dx * 10)  # ~1 if dx > 0, ~0 if dx < 0

        sy = self.sigma_y(torch.abs(dx_km))
        sz = self.sigma_z(torch.abs(dx_km))

        # Gaussian plume equation
        lateral = torch.exp(-dy**2 / (2 * sy**2))
        
        vertical = (
            torch.exp(-(dz - H)**2 / (2 * sz**2))
            + torch.exp(-(dz + H)**2 / (2 * sz**2))
        )

        concentration = (Q / (2 * np.pi * u * sy * sz)) * lateral * vertical
        concentration = concentration * downwind_mask

        return concentration

    def generate_concentration_grid(
        self,
        grid_size: int = 100,
        domain_m: float = 5000,   # Domain size in meters
        wind_speed: float = 3.0,
        z: float = 0.0,          # Ground level
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate a 2D concentration grid for visualization.
        
        Returns: (X_grid, Y_grid, C_grid) as numpy arrays
        """
        x = torch.linspace(-domain_m * 0.2, domain_m, grid_size, dtype=torch.float64)
        y = torch.linspace(-domain_m / 2, domain_m / 2, grid_size, dtype=torch.float64)
        X, Y = torch.meshgrid(x, y, indexing="ij")
        Z = torch.full_like(X, z)

        with torch.no_grad():
            C = self.forward(X.flatten(), Y.flatten(), Z.flatten(), wind_speed)
            C = C.reshape(grid_size, grid_size)

        return X.numpy(), Y.numpy(), C.numpy()
