import numpy as np

def hermite_interpolation(t_points, r_points, t_eval):
    """
    Performs Hermite interpolation as defined in the provided formula.

    Parameters
    ----------
    t_points : array-like
        Known x-values (e.g., maturities, dates as floats).
    r_points : array-like
        Known y-values (e.g., rates corresponding to t_points).
    t_eval : float or array-like
        The x-value(s) at which to evaluate the interpolation.

    Returns
    -------
    r_interp : float or np.ndarray
        The interpolated value(s) at t_eval.
    """
    t_points = np.array(t_points, dtype=float)
    r_points = np.array(r_points, dtype=float)

    n = len(t_points)
    h = np.diff(t_points)
    slopes = np.diff(r_points) / h

    # Compute boundary derivatives (natural Hermite style)
    r_prime = np.zeros(n)
    r_prime[0] = ((2 * h[0] + h[1]) * slopes[0] - h[0] * slopes[1]) / (h[0] + h[1])
    r_prime[-1] = ((2 * h[-1] + h[-2]) * slopes[-1] - h[-1] * slopes[-2]) / (h[-1] + h[-2])

    # Interior derivatives
    for i in range(1, n - 1):
        r_prime[i] = ((h[i] * slopes[i - 1]) + (h[i - 1] * slopes[i])) / (h[i - 1] + h[i])

    def hermite_segment(i, t):
        """Evaluate Hermite interpolation on segment i."""
        t0, t1 = t_points[i], t_points[i + 1]
        r0, r1 = r_points[i], r_points[i + 1]
        r0p, r1p = r_prime[i], r_prime[i + 1]

        m = (t - t0) / (t1 - t0)

        g1 = (t1 - t0) * r0p
        c1 = (t1 - t0) * r1p

        return (
            (1 - m) * r0
            + m * r1
            + m * (1 - m) * ((1 - m) * (r1 - r0) - (1 - m) * g1 + m * c1)
        )

    # Handle scalar or vector input
    if np.isscalar(t_eval):
        t_eval = np.array([t_eval])
        scalar_output = True
    else:
        t_eval = np.array(t_eval)
        scalar_output = False

    result = np.zeros_like(t_eval, dtype=float)

    for j, t in enumerate(t_eval):
        if t <= t_points[0]:
            result[j] = r_points[0]
        elif t >= t_points[-1]:
            result[j] = r_points[-1]
        else:
            i = np.searchsorted(t_points, t) - 1
            result[j] = hermite_segment(i, t)

    return result[0] if scalar_output else result