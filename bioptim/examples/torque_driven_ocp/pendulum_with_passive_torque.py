"""
This is a clone of the example/getting_started/pendulum.py where a pendulum must be balance. The difference is that
this time there is a passive torque which is applied on Seg1 in the model "pendulum_with_passive_torque.bioMod".
The expression of the tau is therefore not the same here.
"""

import biorbd_casadi as biorbd

from bioptim import (
    OptimalControlProgram,
    DynamicsFcn,
    Dynamics,
    Bounds,
    QAndQDotBounds,
    InitialGuess,
    ObjectiveFcn,
    Objective,
    OdeSolver,
    CostType,
    Solver,
    BiorbdModel,
    RigidBodyDynamics,
)


def prepare_ocp(
    biorbd_model_path: str,
    final_time: float,
    n_shooting: int,
    ode_solver: OdeSolver = OdeSolver.RK4(),
    rigidbody_dynamics=RigidBodyDynamics.ODE,
    with_passive_torque=False,
) -> OptimalControlProgram:
    """
    The initialization of an ocp

    Parameters
    ----------
    biorbd_model_path: str
        The path to the biorbd model
    final_time: float
        The time in second required to perform the task
    n_shooting: int
        The number of shooting points to define int the direct multiple shooting program
    ode_solver: OdeSolver = OdeSolver.RK4()
        Which type of OdeSolver to use
    use_sx: bool
        If the SX variable should be used instead of MX (can be extensive on RAM)
    n_threads: int
        The number of threads to use in the paralleling (1 = no parallel computing)
    rigidbody_dynamics : RigidBodyDynamics
        rigidbody dynamics DAE or ODE
    with_passive_torque: bool
        If the passive torque is used in dynamics

    Returns
    -------
    The OptimalControlProgram ready to be solved
    """

    bio_model = BiorbdModel(biorbd_model_path)

    # Add objective functions
    objective_functions = Objective(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau")

    # Dynamics
    dynamics = Dynamics(
        DynamicsFcn.TORQUE_DRIVEN, rigidbody_dynamics=rigidbody_dynamics, with_passive_torque=with_passive_torque
    )

    # Path constraint
    x_bounds = QAndQDotBounds(bio_model)
    x_bounds[:, [0, -1]] = 0
    x_bounds[1, -1] = 3.14

    # Initial guess
    n_q = bio_model.nb_q
    n_qdot = bio_model.nb_qdot
    x_init = InitialGuess([0] * (n_q + n_qdot))

    # Define control path constraint
    n_tau = bio_model.nb_tau
    tau_min, tau_max, tau_init = -100, 100, 0
    u_bounds = Bounds([tau_min] * n_tau, [tau_max] * n_tau)
    u_bounds[1, :] = 0  # Prevent the model from actively rotate

    u_init = InitialGuess([tau_init] * n_tau)

    return OptimalControlProgram(
        bio_model,
        dynamics,
        n_shooting,
        final_time,
        x_init=x_init,
        u_init=u_init,
        x_bounds=x_bounds,
        u_bounds=u_bounds,
        objective_functions=objective_functions,
        ode_solver=ode_solver,
    )


def main():
    """
    If pendulum is run as a script, it will perform the optimization and animates it
    """

    # --- Prepare the ocp --- #
    ocp = prepare_ocp(
        biorbd_model_path="models/pendulum_with_passive_torque.bioMod",
        final_time=1,
        n_shooting=30,
        with_passive_torque=False,
    )

    # Custom plots
    ocp.add_plot_penalty(CostType.ALL)

    # --- Print ocp structure --- #
    ocp.print(to_console=False, to_graph=False)

    # --- Solve the ocp --- #
    sol = ocp.solve(Solver.IPOPT(show_online_optim=True))
    # sol.graphs()

    # --- Show the results in a bioviz animation --- #
    sol.detailed_cost_values()
    sol.print_cost()
    sol.animate(n_frames=100)


if __name__ == "__main__":
    main()
