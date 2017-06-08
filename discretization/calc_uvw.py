"""
Discretizes and solves momentum equation (all three components).
"""

# Standard Python modules
from standard import *

# PyNS modules
from constants.all      import *
from operators.all      import *

from discretization.adj_n_bnds     import adj_n_bnds
from discretization.adj_o_bnds     import adj_o_bnds
from discretization.advection      import advection
from discretization.create_matrix  import create_matrix
from discretization.obst_zero_val  import obst_zero_val

# =============================================================================
def calc_uvw(uvw, uvwf, rho, mu, p_tot, e_f, dt, dxyz, obst):
# -----------------------------------------------------------------------------
  """
  Args:
    uvw:   Tuple with three velocity components, staggered or collocated. 
           (Each component is created with "create_unknown" function.)
    uvwf:  Tuple with three staggered velocity components (where each 
           component is created with "pyns.create_unknown" function.
    rho:   Three-dimensional matrix holding density for all cells.
    mu:    Three-dimensional matrix holding dynamic viscosity.
    p_tot: Three-dimensional matrix holding total pressure.
    e_f:   Tuple containing three-dimensional matrices holding external 
           forces in each direction.
    dt:    Time step.
    dxyz:  Tuple holding cell dimensions in "x", "y" and "z" directions.
           Each cell dimension is a three-dimensional matrix.
    obst:  Obstacle, three-dimensional matrix with zeros and ones.  It is
           zero in fluid, one in solid.

  Returns:
    none, but input argument uvw is modified!      
  """

  # Unpack tuples
  u,   v,   w   = uvw
  uf,  vf,  wf  = uvwf
  dx,  dy,  dz  = dxyz
  e_x, e_y, e_z = e_f

  # Fetch resolutions
  ru = u.val.shape
  rv = v.val.shape
  rw = w.val.shape
  
  # Pre-compute geometrical quantities
  dv = dx * dy * dz

  d = u.pos

  # Create linear systems
  A_u, b_u = create_matrix(u, rho/dt, mu, dxyz, obst, DIRICHLET)
  A_v, b_v = create_matrix(v, rho/dt, mu, dxyz, obst, DIRICHLET)
  A_w, b_w = create_matrix(w, rho/dt, mu, dxyz, obst, DIRICHLET)
 
  # Advection terms for momentum                            
  c_u = advection(rho, u, uvwf, dxyz, dt, 'superbee');
  c_v = advection(rho, v, uvwf, dxyz, dt, 'superbee');
  c_w = advection(rho, w, uvwf, dxyz, dt, 'superbee');

  # Innertial term for momentum (this works for collocated and staggered)
  i_u = u.old * avg(u.pos, rho) * avg(u.pos, dv) / dt
  i_v = v.old * avg(v.pos, rho) * avg(v.pos, dv) / dt
  i_w = w.old * avg(w.pos, rho) * avg(w.pos, dv) / dt
  
  # Compute staggered pressure gradients
  p_tot_x = dif_x(p_tot) / avg_x(dx)
  p_tot_y = dif_y(p_tot) / avg_y(dy)
  p_tot_z = dif_z(p_tot) / avg_z(dz)

  # Make pressure gradients cell-centered
  if d == C:
    p_tot_x = avg_x(cat_x((p_tot_x[:1,:,:], p_tot_x, p_tot_x[-1:,:,:])))
    p_tot_y = avg_y(cat_y((p_tot_y[:,:1,:], p_tot_y, p_tot_y[:,-1:,:])))
    p_tot_z = avg_z(cat_z((p_tot_z[:,:,:1], p_tot_z, p_tot_z[:,:,-1:])))

  # Total pressure gradients (this works for collocated and staggered)
  p_st_u = p_tot_x * avg(u.pos, dv)
  p_st_v = p_tot_y * avg(v.pos, dv)
  p_st_w = p_tot_z * avg(w.pos, dv)
  
  # Full force terms for momentum equations (collocated and staggered)
  f_u = b_u - c_u + i_u - p_st_u + e_x * avg(u.pos, dv)
  f_v = b_v - c_v + i_v - p_st_v + e_y * avg(v.pos, dv)
  f_w = b_w - c_w + i_w - p_st_w + e_z * avg(w.pos, dv)

  # Take care of obsts in the domian
  if obst.any() != 0:
    f_u = obst_zero_val(u.pos, f_u, obst)
    f_v = obst_zero_val(v.pos, f_v, obst)
    f_w = obst_zero_val(w.pos, f_w, obst)

  # Solve for velocities
  res0 = bicgstab( A_u, reshape(f_u, prod(ru)), tol=TOL )
  res1 = bicgstab( A_v, reshape(f_v, prod(rv)), tol=TOL )
  res2 = bicgstab( A_w, reshape(f_w, prod(rw)), tol=TOL )
  u.val[:] = reshape(res0[0], ru)
  v.val[:] = reshape(res1[0], rv)
  w.val[:] = reshape(res2[0], rw)

  # Update velocities in boundary cells
  adj_o_bnds((u,v,w), (dx,dy,dz), dt)

  # Update face velocities (also substract cell-centered pressure gradients 
  #                         and add staggered pressure gradients)
  if d == C:
    uf.val[:] = avg_x(u.val + dt /       rho  * (      p_tot_x     ))       \
                            - dt / avg_x(rho) * (dif_x(p_tot) / avg_x(dx))  
    vf.val[:] = avg_y(v.val + dt /       rho  * (      p_tot_y     ))       \
                            - dt / avg_y(rho) * (dif_y(p_tot) / avg_y(dy))  
    wf.val[:] = avg_z(w.val + dt /       rho  * (      p_tot_z     ))       \
                            - dt / avg_z(rho) * (dif_z(p_tot) / avg_z(dz))  

    for j in (W,E):
      uf.bnd[j].val[:] = u.bnd[j].val[:]  
      vf.bnd[j].val[:] = avg_y(v.bnd[j].val[:])
      wf.bnd[j].val[:] = avg_z(w.bnd[j].val[:])  
    for j in (S,N):
      uf.bnd[j].val[:] = avg_x(u.bnd[j].val[:])
      vf.bnd[j].val[:] = v.bnd[j].val[:]
      wf.bnd[j].val[:] = avg_z(w.bnd[j].val[:])  
    for j in (B,T):  
      uf.bnd[j].val[:] = avg_x(u.bnd[j].val[:])
      vf.bnd[j].val[:] = avg_y(v.bnd[j].val[:])
      wf.bnd[j].val[:] = w.bnd[j].val[:]  

  else:
    uf.val[:] = u.val[:]
    vf.val[:] = v.val[:]
    wf.val[:] = w.val[:]
    for j in (W,E,S,N,B,T):
      uf.bnd[j].val[:] = u.bnd[j].val[:]
      vf.bnd[j].val[:] = v.bnd[j].val[:]
      wf.bnd[j].val[:] = w.bnd[j].val[:]

  if obst.any() != 0:
    uf.val[:] = obst_zero_val(X, uf.val, obst)
    vf.val[:] = obst_zero_val(Y, vf.val, obst)
    wf.val[:] = obst_zero_val(Z, wf.val, obst)

  return  # end of function