"""
This example mimics by essence what a jumper does which is maximizing the predicted height of the
center of mass at the peak of an aerial phase. It does so with a very simple two segments model though.
It is designed to give a sense of the goal of the different MINIMIZE_COM functions and the use of
weight=-1 to maximize instead of minimizing.
"""

import biorbd
import numpy as np
from bioptim import (
    OptimalControlProgram,
    ObjectiveList,
    ObjectiveFcn,
    DynamicsList,
    DynamicsFcn,
    BiMapping,
    BoundsList,
    QAndQDotBounds,
    InitialGuessList,
    OdeSolver,
    Axis,
    ConstraintList,
    ConstraintFcn,
    Node,
)


def prepare_ocp(
    model_path: str,
    phase_time: float,
    n_shooting: int,
    use_actuators: bool = False,
    ode_solver: OdeSolver = OdeSolver.RK4,
    objective_name: str = "MINIMIZE_PREDICTED_COM_HEIGHT",
    com_constraints: bool = False,
) -> OptimalControlProgram:
    """
    Prepare the ocp

    Parameters
    ----------
    model_path: str
        The path to the bioMod file
    phase_time: float
        The time at the final node
    n_shooting: int
        The number of shooting points
    use_actuators: bool
        If torque or torque activation should be used for the dynamics
    ode_solver: OdeSolver
        The ode solver to use
    objective_name: str
        The objective function to run ('MINIMIZE_PREDICTED_COM_HEIGHT',
        'MINIMIZE_COM_POSITION' or 'MINIMIZE_COM_VELOCITY')
    com_constraints: bool
        If a constraint on the COM should be applied

    Returns
    -------
    The OptimalControlProgram ready to be solved
    """

    biorbd_model = biorbd.Model(model_path)

    if use_actuators:
        tau_min, tau_max, tau_init = -1, 1, 0
    else:
        tau_min, tau_max, tau_init = -500, 500, 0

    tau_mapping = BiMapping([None, None, None, 0], [3])

    # Add objective functions
    objective_functions = ObjectiveList()
    if objective_name == "MINIMIZE_PREDICTED_COM_HEIGHT":
        objective_functions.add(ObjectiveFcn.Mayer.MINIMIZE_PREDICTED_COM_HEIGHT, weight=-1)
    elif objective_name == "MINIMIZE_COM_POSITION":
        objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_COM_POSITION, axis=Axis.Z, weight=-1)
    elif objective_name == "MINIMIZE_COM_VELOCITY":
        objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_COM_VELOCITY, axis=Axis.Z, weight=-1)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_TORQUE, weight=1 / 100)

    # Dynamics
    dynamics = DynamicsList()
    if use_actuators:
        dynamics.add(DynamicsFcn.TORQUE_ACTIVATIONS_DRIVEN_WITH_CONTACT)
    else:
        dynamics.add(DynamicsFcn.TORQUE_DRIVEN_WITH_CONTACT)

    # Constraints
    constraints = ConstraintList()
    if com_constraints:
        constraints.add(
            ConstraintFcn.TRACK_COM_VELOCITY,
            node=Node.ALL,
            min_bound=np.array([-100, -100, -100]),
            max_bound=np.array([100, 100, 100]),
        )
        constraints.add(
            ConstraintFcn.TRACK_COM_POSITION,
            node=Node.ALL,
            min_bound=np.array([-1, -1, -1]),
            max_bound=np.array([1, 1, 1]),
        )

    # Path constraint
    n_q = biorbd_model.nbQ()
    n_qdot = n_q
    pose_at_first_node = [0, 0, -0.5, 0.5]

    # Initialize x_bounds
    x_bounds = BoundsList()
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model))
    x_bounds[0][:, 0] = pose_at_first_node + [0] * n_qdot

    # Initial guess
    x_init = InitialGuessList()
    x_init.add(pose_at_first_node + [0] * n_qdot)

    # Define control path constraint
    u_bounds = BoundsList()
    u_bounds.add([tau_min] * tau_mapping.to_first.len, [tau_max] * tau_mapping.to_first.len)

    u_init = InitialGuessList()
    u_init.add([tau_init] * tau_mapping.to_first.len)

    return OptimalControlProgram(
        biorbd_model,
        dynamics,
        n_shooting,
        phase_time,
        x_init,
        u_init,
        x_bounds,
        u_bounds,
        objective_functions,
        constraints=constraints,
        tau_mapping=tau_mapping,
        ode_solver=ode_solver,
    )


if __name__ == "__main__":
    """
    Prepares and solves a maximal velocity at center of mass program and animates it
    """

    model_path = "../torque_driven_with_contact/2segments_4dof_2contacts.bioMod"
    t = 0.5
    ns = 20
    ocp = prepare_ocp(
        model_path=model_path,
        phase_time=t,
        n_shooting=ns,
        use_actuators=False,
        objective_name="MINIMIZE_COM_VELOCITY",
        com_constraints=True,
    )

    # --- Solve the program --- #
    sol = ocp.solve(show_online_optim=True)

    # --- Show results --- #
    sol.animate(n_frames=40)
