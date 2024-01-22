"""
This trivial spring example targets to have the highest upward velocity. It is however only able to load a spring by
pulling downward and afterward to let it go so it gains velocity. It is designed to show how one can use the external
forces to interact with the body.
"""

import platform

from casadi import MX, vertcat
import numpy as np
from bioptim import (
    BiorbdModel,
    OptimalControlProgram,
    Dynamics,
    ConfigureProblem,
    Objective,
    DynamicsFunctions,
    ObjectiveFcn,
    BoundsList,
    NonLinearProgram,
    Solver,
    DynamicsEvaluation,
    PhaseDynamics,
    Node,
)


def custom_dynamic(
    time: MX, states: MX, controls: MX, parameters: MX, algebraic_states: MX, nlp: NonLinearProgram
) -> DynamicsEvaluation:
    """
    The dynamics of the system using an external force (see custom_dynamics for more explanation)

    Parameters
    ----------
    time: MX
        The current time of the system
    states: MX
        The current states of the system
    controls: MX
        The current controls of the system
    parameters: MX
        The current parameters of the system
    algebraic_states: MX
        The current algebraic states of the system
    nlp: NonLinearProgram
        A reference to the phase of the ocp

    Returns
    -------
    The state derivative
    """

    q = DynamicsFunctions.get(nlp.states["q"], states)
    qdot = DynamicsFunctions.get(nlp.states["qdot"], states)
    tau = DynamicsFunctions.get(nlp.controls["tau"], controls)

    force_vector = MX.zeros(6)
    force_vector[5] = 100 * q[0] ** 2 #spring force

    qddot = nlp.model.forward_dynamics(q, qdot, tau, external_forces=[["Point", force_vector]])

    return DynamicsEvaluation(dxdt=vertcat(qdot, qddot), defects=None)


def custom_configure(ocp: OptimalControlProgram, nlp: NonLinearProgram):
    """
    The configuration of the dynamics (see custom_dynamics for more explanation)

    Parameters
    ----------
    ocp: OptimalControlProgram
        A reference to the ocp
    nlp: NonLinearProgram
        A reference to the phase of the ocp
    """
    ConfigureProblem.configure_q(ocp, nlp, as_states=True, as_controls=False)
    ConfigureProblem.configure_qdot(ocp, nlp, as_states=True, as_controls=False)
    ConfigureProblem.configure_tau(ocp, nlp, as_states=False, as_controls=True)
    ConfigureProblem.configure_dynamics_function(ocp, nlp, custom_dynamic)


def prepare_ocp(
    biorbd_model_path: str = "models/mass_point.bioMod",
    phase_dynamics: PhaseDynamics = PhaseDynamics.SHARED_DURING_THE_PHASE,
    expand_dynamics: bool = True,
):
    # BioModel path
    m = BiorbdModel(biorbd_model_path)
    m.set_gravity(np.array((0, 0, 0)))

    # Add objective functions (high upward velocity at end point)
    objective_functions = Objective(ObjectiveFcn.Mayer.MINIMIZE_STATE, key="qdot", index=0, weight=-1,
                                    node=Node.END,)# quadratic=False)

    # Dynamics
    dynamics = Dynamics(
        custom_configure,
        dynamic_function=custom_dynamic,
        expand_dynamics=expand_dynamics,
        phase_dynamics=phase_dynamics,
    )

    # Path constraint
    x_bounds = BoundsList()
    x_bounds["q"] = [-1] * m.nb_q, [1] * m.nb_q
    x_bounds["q"][:, 0] = 0
    x_bounds["qdot"] = [-100] * m.nb_qdot, [100] * m.nb_qdot
    x_bounds["qdot"][:, 0] = 0

    # Define control path constraint
    u_bounds = BoundsList()
    u_bounds["tau"] = [-100] * m.nb_tau, [0] * m.nb_tau

    return OptimalControlProgram(
        m,
        dynamics,
        n_shooting=30,
        phase_time=0.5,
        x_bounds=x_bounds,
        u_bounds=u_bounds,
        objective_functions=objective_functions,
    )


def main():
    ocp = prepare_ocp()
    ocp.print(to_graph=True, to_console=False)
    # --- Solve the program --- #
    sol = ocp.solve(Solver.IPOPT(show_online_optim=platform.system() == "Linux"))




    import matplotlib
    from matplotlib import pyplot as plt
    matplotlib.use('Qt5Agg')

    states = sol.decision_states()
    controls = sol.decision_controls()

    q = np.array([item.flatten() for item in states["q"]])
    qdot = np.array([item.flatten() for item in states["qdot"]])
    tau = np.vstack([
        np.array([item.flatten() for item in controls["tau"]]),
        np.array([[np.nan]])
    ])
    time = np.array([item.full().flatten()[0] for item in sol.stepwise_time()])


    fig, axs = plt.subplots(2, 2, figsize=(10, 15))

    # Plotting q solutions for both DOFs
    axs[0, 0].plot(time, q)
    axs[0, 0].set_title("Joint coordinates")
    axs[0, 0].set_ylabel("q")
    axs[0, 0].set_xlabel("Time [s]")
    axs[0, 0].grid(True)

    axs[0, 1].plot(time, qdot)
    axs[0, 1].set_title("Joint velocities")
    axs[0, 1].set_ylabel("qdot")
    axs[0, 1].set_xlabel("Time [s]")
    axs[0, 1].grid(True)

    axs[1, 0].step(time, tau)
    axs[1, 0].set_title("Generalized forces")
    axs[1, 0].set_ylabel("tau")
    axs[1, 0].set_xlabel("Time [s]")
    axs[1, 0].grid(True)

    plt.tight_layout()
    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.3)

    # Display the plot
    plt.show()

    # --- Show results --- #
    sol.animate()


if __name__ == "__main__":
    main()
