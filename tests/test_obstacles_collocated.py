"""
#                                                       o ... scalars
#                          (n)                          - ... u velocities
#                                                       | ... v velocities
#       +-------+-------+-------+-------+-------+
#       |       |       |       |       |       |
#       |   o   -   o   -   o   -   o   -   o   | j=ny-1
#       |       |       |       |       |       |
#       +---|---+---|---+---|---+---|---+---|---+     j=ny-2
#       |       |       |       |       |       |
#       |   o   -   o   -   o   -   o   -   o   | ...
#       |       |       |       |       |       |
#  (w)  +---|---+---|---+---|---+---|---+---|---+    j=1        (e)
#       |       |       |       |       |       |
#       |   o   -   o   -   o   -   o   -   o   | j=1
#       |       |       |       |       |       |
#       +---|---+---|---+---|---+---|---+---|---+    j=0 (v-velocity)
#       |       |       |       |       |       |
#       |   o   -   o   -   o   -   o   -   o   | j=0   (scalar cell)
#       |       |       |       |       |       |
#       +-------+-------+-------+-------+-------+
#  y       i=0     i=1     ...     ...    i=nx-1      (scalar cells)
# ^            i=0      i=1    ...    i=nx-2      (u-velocity cells)
# |
# +---> x                  (s)
#
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

def main(show_plot=True, time_steps=4800, plot_freq=480):

# =============================================================================
#
# Define problem
#
# =============================================================================

    # Node coordinates
    xn = nodes(0, 1,     256)
    yn = nodes(0, 0.125,  32)
    zn = nodes(0, 0.125,   4)

    # Cell coordinates
    xc = avg(xn)
    yc = avg(yn)
    zc = avg(zn)

    # Cell dimensions
    nx,ny,nz, dx,dy,dz, rc,ru,rv,rw = cartesian_grid(xn,yn,zn)

    # Set physical properties
    rho, mu, cap, kappa = properties.air(rc)

    # Time-stepping parameters
    dt  = 0.002      # time step
    ndt = time_steps # number of time steps

    # Create unknowns; names, positions and sizes
    uc = Unknown('cell-u-vel',  C, rc, DIRICHLET)
    vc = Unknown('cell-v-vel',  C, rc, DIRICHLET)
    wc = Unknown('cell-w-vel',  C, rc, DIRICHLET)
    uf = Unknown('face-u-vel',  X, ru, DIRICHLET)
    vf = Unknown('face-v-vel',  Y, rv, DIRICHLET)
    wf = Unknown('face-w-vel',  Z, rw, DIRICHLET)
    p  = Unknown('pressure',    C, rc, NEUMANN)

    # Specify boundary conditions
    uc.bnd[W].typ[:1,:,:] = DIRICHLET
    for k in range(0,nz):
        uc.bnd[W].val[:1,:,k]  = par(0.1, yn)

    uc.bnd[E].typ[:1,:,:] = OUTLET

    for j in (B,T):
        uf.bnd[j].typ[:] = NEUMANN
        vf.bnd[j].typ[:] = NEUMANN
        wf.bnd[j].typ[:] = NEUMANN

    obst = zeros(rc)
    for j in range(0, 24):
        for i in range(64+j, 64+24):
            for k in range(0,nz):
                obst[i,j,k] = 1

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
        uc.old[:] = uc.val[:]
        vc.old[:] = vc.val[:]
        wc.old[:] = wc.val[:]

        # ----------------------
        # Momentum conservation
        # ----------------------
        ef = zeros(rc), zeros(rc), zeros(rc)

        calc_uvw((uc,vc,wc), (uf,vf,wf), rho, mu,
                 zeros(rc), ef, dt, (dx,dy,dz), obst)

        # ---------
        # Pressure
        # ---------
        calc_p(p, (uf,vf,wf), rho, dt, (dx,dy,dz), obst)

        # --------------------
        # Velocity correction
        # --------------------
        corr_uvw((uc,vc,wc), p, rho, dt, (dx,dy,dz), obst)
        corr_uvw((uf,vf,wf), p, rho, dt, (dx,dy,dz), obst)

        # Compute volume balance for checking
        err = vol_balance((uf,vf,wf), (dx,dy,dz), obst)
        print('Maximum volume error after correction: %12.5e' % abs(err).max())

        # Check the CFL number too
        cfl = cfl_max((uc,vc,wc), dt, (dx,dy,dz))
        print('Maximum CFL number: %12.5e' % cfl)

# =============================================================================
#
# Visualisation
#
# =============================================================================
        if show_plot:
            if ts % plot_freq == 0:
                plot.isolines(p.val, (uc,vc,wc), (xn,yn,zn), Z)
                plot.tecplot("obst-staggered-%6.6d.plt" % ts, 
                             (xn, yn, zn), (uf, vf, wf, p))

if __name__ == '__main__':
    main()
