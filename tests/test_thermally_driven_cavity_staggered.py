"""
This program solves thermally driven cavity at Ra = 1.0e6, in dimensional
and non-dimensional forms, for staggered variable arrangement.

Equations in dimensional form:

D(rho u)/Dt = nabla(mu (nabla u)^T) - nabla p + g
D(rho cp T)/Dt = nabla(lambda (nabla T)^T)

Equations in non-dimensional form, for natural convection problems

DU/Dt = nabla(1/sqrt(Gr) (nabla U)^T) - nabla P + theta
D theta/Dt = nabla(1/(Pr*sqrt(Gr)) (nabla theta)^T)

For thermally driven cavity, with properties of air at 60 deg:

nu   =  1.89035E-05;
beta =  0.003;
dT   = 17.126;
L    =  0.1;
Pr   = 0.709;

Characteristic non-dimensional numbers are:
Gr = 1.4105E+06
Ra = 1.0000E+06
"""

#!/usr/bin/python

# Standard Python modules
from pyns.standard import *

# PyNS modules
from pyns.constants      import *
from pyns.operators      import *
from pyns.discretization import *
from pyns.display        import plot, write
from pyns.physical       import properties
        
def main(show_plot=True, time_steps=1200, plot_freq=120):

#==============================================================================
#
# Define problem
#
#==============================================================================

    xn = nodes(0, 1,  64, 1.0/256, 1.0/256)
    yn = nodes(0, 1,  64, 1.0/256, 1.0/256)
    zn = nodes(0, 0.1, 5)

    # Cell dimensions
    nx,ny,nz, dx,dy,dz, rc,ru,rv,rw = cartesian_grid(xn,yn,zn)

    # Set physical properties
    grashof = 1.4105E+06
    prandtl = 0.7058
    rho   = zeros(rc)
    mu    = zeros(rc)
    kappa = zeros(rc)
    cap   = zeros(rc)
    rho  [:,:,:] = 1.0
    mu   [:,:,:] = 1.0 / sqrt(grashof)
    kappa[:,:,:] = 1.0 / (prandtl * sqrt(grashof))
    cap  [:,:,:] = 1.0

    # Time-stepping parameters
    dt  = 0.02        # time step
    ndt = time_steps  # number of time steps

    # Create unknowns; names, positions and sizes
    uf = Unknown('face-u-vel',  X, ru, DIRICHLET)
    vf = Unknown('face-v-vel',  Y, rv, DIRICHLET)
    wf = Unknown('face-w-vel',  Z, rw, DIRICHLET)
    t  = Unknown('temperature', C, rc, NEUMANN)
    p  = Unknown('pressure',    C, rc, NEUMANN)
    p_tot = zeros(rc)

    # This is a new test
    t.bnd[W].typ[:] = DIRICHLET
    t.bnd[W].val[:] = -0.5

    t.bnd[E].typ[:] = DIRICHLET
    t.bnd[E].val[:] = +0.5

    for j in (B,T):
        uf.bnd[j].typ[:] = NEUMANN
        vf.bnd[j].typ[:] = NEUMANN
        wf.bnd[j].typ[:] = NEUMANN

    obst = zeros(rc)

# =============================================================================
#
# Solution algorithm
#
# =============================================================================

    # ----------
    #
    # Time loop
    #
    # ----------
    for ts in range(1,ndt+1):

        write.time_step(ts)

        # -----------------
        # Store old values
        # -----------------
        t.old[:]  = t.val[:]
        uf.old[:] = uf.val[:]
        vf.old[:] = vf.val[:]
        wf.old[:] = wf.val[:]

        # -----------------------
        # Temperature (enthalpy)
        # -----------------------
        calc_t(t, (uf,vf,wf), (rho*cap), kappa, dt, (dx,dy,dz), obst)

        # ----------------------
        # Momentum conservation
        # ----------------------
        ef = zeros(ru), avg(Y,t.val), zeros(rw)

        calc_uvw((uf,vf,wf), (uf,vf,wf), rho, mu,  \
                 p_tot, ef, dt, (dx,dy,dz), obst)

        # ---------
        # Pressure
        # ---------
        calc_p(p, (uf,vf,wf), rho, dt, (dx,dy,dz), obst)

        p_tot = p_tot + p.val

        # --------------------
        # Velocity correction
        # --------------------
        corr_uvw((uf,vf,wf), p, rho, dt, (dx,dy,dz), obst)

        # Compute volume balance for checking
        err = vol_balance((uf,vf,wf), (dx,dy,dz), obst)
        print('Maximum volume error after correction: %12.5e' % abs(err).max())

        # Check the CFL number too
        cfl = cfl_max((uf,vf,wf), dt, (dx,dy,dz))
        print('Maximum CFL number: %12.5e' % cfl)

# =============================================================================
#
# Visualisation
#
# =============================================================================
        if show_plot:
            if ts % plot_freq == 0:
                plot.isolines(t.val, (uf, vf, wf), (xn, yn, zn), Z)
                plot.gmv("tdc-staggered-%6.6d.gmv" % ts, 
                         (xn, yn, zn), (uf, vf, wf, t))

if __name__ == '__main__':
    main()
