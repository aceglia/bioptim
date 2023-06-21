from bioptim import (
    BiorbdModel,
    OptimalControlProgram,
    DynamicsList,
    DynamicsFcn,
    ObjectiveList,
    ConstraintList,
    ConstraintFcn,
    BoundsList,
    InitialGuessList,
    Node,
    ObjectiveFcn,
    BiMappingList,
    Axis,
    Solver,
)


def prepare_ocp(
    biorbd_model_path_with_translations: str = "models/double_pendulum_with_translations.bioMod",
    n_shooting: tuple = (40, 40),
    assume_phase_dynamics: bool = True,
) -> OptimalControlProgram:
    bio_model = (BiorbdModel(biorbd_model_path_with_translations), BiorbdModel(biorbd_model_path_with_translations))

    # Problem parameters
    final_time = (1.5, 2.5)
    tau_min, tau_max = -200, 200

    # Mapping
    tau_mappings = BiMappingList()
    tau_mappings.add("tau", to_second=[0, 1, None, 2], to_first=[0, 1, 3], phase=0)
    tau_mappings.add("tau", to_second=[None, None, None, 0], to_first=[3], phase=1)

    # Add objective functions
    objective_functions = ObjectiveList()
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau", weight=1, phase=0)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_CONTROL, key="tau", weight=1, phase=1)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_STATE, key="q", weight=0.01, phase=0)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_STATE, key="q", weight=0.01, phase=1)
    objective_functions.add(
        ObjectiveFcn.Mayer.MINIMIZE_COM_POSITION, node=Node.END, weight=-1000, axes=Axis.Z, phase=1, quadratic=False
    )
    objective_functions.add(
        ObjectiveFcn.Mayer.MINIMIZE_STATE, key="q", index=2, node=Node.END, weight=-100, phase=1, quadratic=False
    )

    # Constraints
    constraints = ConstraintList()
    constraints.add(ConstraintFcn.TIME_CONSTRAINT, node=Node.END, min_bound=0.3, max_bound=3, phase=0)
    constraints.add(ConstraintFcn.TIME_CONSTRAINT, node=Node.END, min_bound=0.3, max_bound=3, phase=1)

    # Dynamics
    dynamics = DynamicsList()
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN, with_contact=False)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN, with_contact=False)

    # Path constraint
    x_bounds = BoundsList()
    x_bounds.add("q", bounds=bio_model[0].bounds_from_ranges("q"), phase=0)
    x_bounds.add("qdot", bounds=bio_model[0].bounds_from_ranges("qdot"), phase=0)
    x_bounds.add("q", bounds=bio_model[1].bounds_from_ranges("q"), phase=1)
    x_bounds.add("qdot", bounds=bio_model[1].bounds_from_ranges("qdot"), phase=1)

    # Phase 0
    # bound constraining the model not to use the two first DoFs
    x_bounds[0]["q"][[0, 1], :] = 0
    x_bounds[0]["qdot"][[0, 1], :] = 0

    x_bounds[0]["q"][2, 0] = 3.14
    x_bounds[0]["q"].min[2, -1] = 2 * 3.14

    # Phase 1
    x_bounds[1]["q"][[0, 1], 0] = 0
    x_bounds[1]["qdot"][[0, 1], 0] = 0
    x_bounds[1]["q"].min[2, -1] = 3 * 3.14

    # Initial guess
    x_init = InitialGuessList()
    x_init.add("q", [1] * bio_model[1].nb_q, phase=1)
    x_init.add("qdot", [1] * bio_model[1].nb_qdot, phase=1)

    # Define control path constraint
    u_bounds = BoundsList()
    u_bounds.add(
        "tau",
        min_bound=[tau_min] * len(tau_mappings[0]["tau"].to_first),
        max_bound=[tau_max] * len(tau_mappings[0]["tau"].to_first),
        phase=0,
    )
    u_bounds.add(
        "tau",
        min_bound=[tau_min] * len(tau_mappings[1]["tau"].to_first),
        max_bound=[tau_max] * len(tau_mappings[1]["tau"].to_first),
        phase=1,
    )

    return OptimalControlProgram(
        bio_model,
        dynamics,
        n_shooting,
        final_time,
        x_bounds=x_bounds,
        u_bounds=u_bounds,
        x_init=x_init,
        objective_functions=objective_functions,
        constraints=constraints,
        variable_mappings=tau_mappings,
        assume_phase_dynamics=assume_phase_dynamics,
    )


def main():
    # --- Prepare the ocp --- #
    ocp = prepare_ocp()

    # --- Solve the program --- #
    sol = ocp.solve(Solver.IPOPT(show_online_optim=False, show_options=dict(show_bounds=True)))

    # --- Show results --- #
    sol.animate()


if __name__ == "__main__":
    main()
