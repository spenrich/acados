#
# Copyright 2019 Gianluca Frison, Dimitris Kouzoupis, Robin Verschueren,
# Andrea Zanelli, Niels van Duijkeren, Jonathan Frey, Tommaso Sartor,
# Branimir Novoselnik, Rien Quirynen, Rezart Qelibari, Dang Doan,
# Jonas Koenemann, Yutao Chen, Tobias Schöls, Jonas Schlagenhauf, Moritz Diehl
#
# This file is part of acados.
#
# The 2-Clause BSD License
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.;
#

from acados_template import *
import numpy as nmp
from ctypes import *
import matplotlib
import matplotlib.pyplot as plt
import scipy.linalg

CODE_GEN = 1
COMPILE = 1

FORMULATION = 2 # 0 for hexagon 2 SCQP sphere

i_d_ref = 1.484
i_q_ref = 1.429
w_val   = 200

i_d_ref = -20
i_q_ref = 20
w_val   = 300

udc = 580
u_max = 2/3*udc

# fitted psi_d map
def psi_d_num(x,y):
    #    This function was generated by the Symbolic Math Toolbox version 8.0.
    #    07-Feb-2018 23:07:49

    psi_d_expression = x*(-4.215858085639979e-3) + \
        exp(y**2*(-8.413493151721978e-5))* \
        atan(x*1.416834085282644e-1)*8.834738694115108e-1

    return psi_d_expression

def psi_q_num(x,y):
    #    This function was generated by the Symbolic Math Toolbox version 8.0.
    #    07-Feb-2018 23:07:50

    psi_q_expression = y*1.04488335702649e-2+ \
        exp(x**2*(-1.0/7.2e1))*atan(y)*6.649036351062812e-2

    return psi_q_expression

psi_d_ref = psi_d_num(i_d_ref, i_q_ref)
psi_q_ref = psi_q_num(i_d_ref, i_q_ref)

# compute steady-state u
Rs      = 0.4
u_d_ref = Rs*i_d_ref - w_val*psi_q_ref
u_q_ref = Rs*i_q_ref + w_val*psi_d_ref

def export_rsm_model():

    model_name = 'rsm'

    # constants
    theta = 0.0352
    Rs = 0.4
    m_load = 0.0
    J = nmp.array([[0, -1], [1, 0]])

    # set up states
    psi_d = SX.sym('psi_d')
    psi_q = SX.sym('psi_q')
    x = vertcat(psi_d, psi_q)

    # set up controls
    u_d = SX.sym('u_d')
    u_q = SX.sym('u_q')
    u = vertcat(u_d, u_q)

    # set up algebraic variables
    i_d = SX.sym('i_d')
    i_q = SX.sym('i_q')
    z = vertcat(i_d, i_q)

    # set up xdot
    psi_d_dot = SX.sym('psi_d_dot')
    psi_q_dot = SX.sym('psi_q_dot')
    xdot = vertcat(psi_d_dot, psi_q_dot)

    # set up parameters
    w      = SX.sym('w') # speed
    dist_d = SX.sym('dist_d') # d disturbance
    dist_q = SX.sym('dist_q') # q disturbance
    p      = vertcat(w, dist_d, dist_q)

    # build flux expression
    Psi = vertcat(psi_d_num(i_d, i_q), psi_q_num(i_d, i_q))

    # dynamics
    f_impl = vertcat(   psi_d_dot - u_d + Rs*i_d - w*psi_q - dist_d, \
                        psi_q_dot - u_q + Rs*i_q + w*psi_d - dist_q, \
                        psi_d - Psi[0], \
                        psi_q - Psi[1])

    model = AcadosModel()

    model.f_impl_expr = f_impl
    model.f_expl_expr = []
    model.x = x
    model.xdot = xdot
    model.u = u
    model.z = z
    model.p = p
    model.name = model_name

    # BGP constraint
    r = SX.sym('r', 2, 1)
    model.con_phi_expr = r[0]**2 + r[1]**2
    model.con_r_expr = vertcat(u_d, u_q)
    model.con_r_in_phi = r

    return model

def get_general_constraints_DC(u_max):

    # polytopic constraint on the input
    r = u_max

    x1 = r
    y1 = 0
    x2 = r*cos(pi/3)
    y2 = r*sin(pi/3)

    q1 = -(y2 - y1/x1*x2)/(1-x2/x1)
    m1 = -(y1 + q1)/x1

    # q1 <= uq + m1*ud <= -q1
    # q1 <= uq - m1*ud <= -q1

    # box constraints
    m2 = 0
    q2 = r*sin(pi/3)
    # -q2 <= uq  <= q2

    # form D and C matrices
    # (acados C interface works with column major format)
    D = nmp.transpose(nmp.array([[1, m1],[1, -m1]]))
    D = nmp.array([[m1, 1],[-m1, 1]])
    C = nmp.transpose(nmp.array([[0, 0], [0, 0]]))

    ug  = nmp.array([-q1, -q1])
    lg  = nmp.array([+q1, +q1])
    lbu = nmp.array([-q2])
    ubu = nmp.array([+q2])

    res = dict()
    res["D"] = D
    res["C"] = C
    res["lg"] = lg
    res["ug"] = ug
    res["lbu"] = lbu
    res["ubu"] = ubu

    return res

# create ocp object to formulate the OCP
ocp = AcadosOcp()

# export model
model = export_rsm_model()
ocp.model = model

if FORMULATION == 2:
    # constraints name
    ocp.constraints.constr_type = 'BGP'

# Ts  = 0.0016
# Ts  = 0.0012
Ts  = 0.0008
# Ts  = 0.0004

nx  = model.x.size()[0]
nu  = model.u.size()[0]
nz  = model.z.size()[0]
np  = model.p.size()[0]
ny  = nu + nx
ny_e = nx
N   = 2
Tf  = N*Ts

# set dimensions
ocp.dims.nx   = nx
ocp.dims.nz   = nz
ocp.dims.ny   = ny
ocp.dims.ny_e  = ny_e
ocp.dims.nbx  = 0
ocp.dims.nbu  = 1

if FORMULATION == 0:
    ocp.dims.nbu  = 1
    ocp.dims.ng   = 2

if FORMULATION == 1:
    ocp.dims.ng  = 0
    ocp.dims.nh  = 1

if FORMULATION == 2:
    ocp.dims.ng   = 2
    ocp.dims.nr   = 2
    ocp.dims.nphi = 1

ocp.dims.ng_e  = 0
ocp.dims.nbx_e = 0
ocp.dims.nu   = nu
ocp.dims.np   = np
ocp.dims.N    = N

# set cost module
Q = nmp.eye(nx)
Q[0,0] = 5e2
Q[1,1] = 5e2

R = nmp.eye(nu)
R[0,0] = 1e-4
R[1,1] = 1e-4

ocp.cost.W = scipy.linalg.block_diag(Q, R)

Vx = nmp.zeros((ny, nx))
Vx[0,0] = 1.0
Vx[1,1] = 1.0

ocp.cost.Vx = Vx

Vu = nmp.zeros((ny, nu))
Vu[2,0] = 1.0
Vu[3,1] = 1.0
ocp.cost.Vu = Vu

Vz = nmp.zeros((ny, nz))
Vz[0,0] = 0.0
Vz[1,1] = 0.0

ocp.cost.Vz = Vz

Q_e = nmp.eye(nx)
Q_e[0,0] = 1e-3
Q_e[1,1] = 1e-3
ocp.cost.W_e = Q_e

Vx_e = nmp.zeros((ny_e, nx))
Vx_e[0,0] = 1.0
Vx_e[1,1] = 1.0

ocp.cost.Vx_e = Vx_e

ocp.cost.yref  = nmp.zeros((ny, ))
ocp.cost.yref[0]  = psi_d_ref
ocp.cost.yref[1]  = psi_q_ref
ocp.cost.yref[2]  = u_d_ref
ocp.cost.yref[3]  = u_q_ref
ocp.cost.yref_e = nmp.zeros((ny_e, ))
ocp.cost.yref_e[0]  = psi_d_ref
ocp.cost.yref_e[1]  = psi_q_ref

# get D and C
res = get_general_constraints_DC(u_max)
D = res["D"]
C = res["C"]
lg = res["lg"]
ug = res["ug"]
lbu = res["lbu"]
ubu = res["ubu"]

# setting bounds
# lbu <= u <= ubu and lbx <= x <= ubx
ocp.constraints.idxbu = nmp.array([1])

ocp.constraints.lbu = lbu
ocp.constraints.ubu = ubu

if FORMULATION > 0:
    ocp.constraints.lphi = nmp.array([-1.0e8])
    ocp.constraints.uphi = nmp.array([(u_max*sqrt(3)/2)**2])

ocp.constraints.x0 = nmp.array([0.0, -0.0])

if FORMULATION == 0 or FORMULATION == 2:
    # setting general constraints
    # lg <= D*u + C*u <= ug
    ocp.constraints.D   = D
    ocp.constraints.C   = C
    ocp.constraints.lg  = lg
    ocp.constraints.ug  = ug

# setting parameters
ocp.constraints.p = nmp.array([w_val, 0.0, 0.0])

# set QP solver
ocp.solver_options.qp_solver = 'PARTIAL_CONDENSING_HPIPM'
# ocp.solver_options.qp_solver = 'FULL_CONDENSING_HPIPM'
# ocp.solver_options.qp_solver = 'FULL_CONDENSING_QPOASES'
ocp.solver_options.hessian_approx = 'GAUSS_NEWTON'
# ocp.solver_options.integrator_type = 'ERK'
ocp.solver_options.integrator_type = 'IRK'

# set prediction horizon
ocp.solver_options.tf = Tf
ocp.solver_options.nlp_solver_type = 'SQP_RTI'
# ocp.solver_options.nlp_solver_type = 'SQP'

file_name = 'acados_ocp.json'

if CODE_GEN == 1:
    if FORMULATION == 0:
        acados_solver = AcadosOcpSolver(ocp, json_file = file_name)
    if FORMULATION == 1:
        acados_solver = AcadosOcpSolver(ocp, json_file = file_name)
    if FORMULATION == 2:
        acados_solver = AcadosOcpSolver(ocp, json_file = file_name)

if COMPILE == 1:
    # make 
    os.chdir('c_generated_code')
    os.system('make clean')
    os.system('make ocp_shared_lib')
    os.chdir('..')

# closed loop simulation TODO(add proper simulation)
Nsim = 100

simX = nmp.ndarray((Nsim, nx))
simU = nmp.ndarray((Nsim, nu))

for i in range(Nsim):
    status = acados_solver.solve()

    if status != 0:
        raise Exception('acados returned status {}. Exiting.'.format(status))

    # get solution
    x0 = acados_solver.get(0, "x")
    u0 = acados_solver.get(0, "u")

    for j in range(nx):
        simX[i,j] = x0[j]

    for j in range(nu):
        simU[i,j] = u0[j]

    field_name = "u"

    # update initial condition
    x0 = acados_solver.get(1, "x")

    if i > Nsim/3 and i < Nsim/2:
        # update params
        for i in range(N):
            acados_solver.set(i, "p", nmp.array([w_val/2.0, 0, 0]))
    else:
        # update params
        for i in range(N):
            acados_solver.set(i, "p", nmp.array([w_val, 0, 0]))

    acados_solver.set(0, "lbx", x0)
    acados_solver.set(0, "ubx", x0)

    # update initial condition
    x0 = acados_solver.get(1, "x")

    acados_solver.set(0, "lbx", x0)
    acados_solver.set(0, "ubx", x0)

# plot results
t = nmp.linspace(0.0, Ts*Nsim, Nsim)
plt.subplot(4, 1, 1)
plt.step(t, simU[:,0], color='r')
plt.plot([0, Ts*Nsim], [ocp.cost.yref[2], ocp.cost.yref[2]], '--')
plt.title('closed-loop simulation')
plt.ylabel('u_d')
plt.xlabel('t')
plt.grid(True)
plt.subplot(4, 1, 2)
plt.step(t, simU[:,1], color='r')
plt.plot([0, Ts*Nsim], [ocp.cost.yref[3], ocp.cost.yref[3]], '--')
plt.ylabel('u_q')
plt.xlabel('t')
plt.grid(True)
plt.subplot(4, 1, 3)
plt.plot(t, simX[:,0])
plt.plot([0, Ts*Nsim], [ocp.cost.yref[0], ocp.cost.yref[0]], '--')
plt.ylabel('psi_d')
plt.xlabel('t')
plt.grid(True)
plt.subplot(4, 1, 4)
plt.plot(t, simX[:,1])
plt.plot([0, Ts*Nsim], [ocp.cost.yref[1], ocp.cost.yref[1]], '--')
plt.ylabel('psi_q')
plt.xlabel('t')
plt.grid(True)

# plot hexagon
r = u_max

x1 = r
y1 = 0
x2 = r*cos(pi/3)
y2 = r*sin(pi/3)

q1 = -(y2 - y1/x1*x2)/(1-x2/x1)
m1 = -(y1 + q1)/x1

# q1 <= uq + m1*ud <= -q1
# q1 <= uq - m1*ud <= -q1

# box constraints
m2 = 0
q2 = r*sin(pi/3)
# -q2 <= uq  <= q2

plt.figure()
plt.plot(simU[:,0], simU[:,1], 'o')
plt.xlabel('ud')
plt.ylabel('uq')
ud = nmp.linspace(-1.5*u_max, 1.5*u_max, 100)
plt.plot(ud, -m1*ud -q1)
plt.plot(ud, -m1*ud +q1)
plt.plot(ud, +m1*ud -q1)
plt.plot(ud, +m1*ud +q1)
plt.plot(ud, -q2*nmp.ones((100, 1)))
plt.plot(ud, q2*nmp.ones((100, 1)))
plt.grid(True)
ax = plt.gca()
ax.set_xlim([-1.5*u_max, 1.5*u_max])
ax.set_ylim([-1.5*u_max, 1.5*u_max])
circle = plt.Circle((0, 0), u_max*nmp.sqrt(3)/2, color='red', fill=False)
ax.add_artist(circle)

# avoid plotting when running on Travis
if os.environ.get('ACADOS_ON_TRAVIS') is None: 
    plt.show()
