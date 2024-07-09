import os
from openlane.steps import Step
from openlane.flows import Flow
from openlane.state import DesignFormat
from openlane.common import Path

__dir__ = os.path.dirname(os.path.abspath(__file__))


@Step.factory.register()
class AreaDoubler(Step):
    """
    This steps takes a floorplan starting at (0, 0) and doubles the area
    utilized.

    This is a purely demonstrative step and is otherwise useless. Please only
    use this as a basis to create your own plugins.
    """

    id = "Example.AreaDoubler"

    inputs = [DesignFormat.DEF]
    outputs = [DesignFormat.DEF]

    def run(self, state_in):
        out_path = os.path.join(self.step_dir, f"{self.config['DESIGN_NAME']}.def")
        self.run_subprocess(
            [
                "ruby",
                os.path.join(__dir__, "scripts", "double_area.rb"),
                state_in[DesignFormat.DEF],
                out_path,
            ]
        )

        return {DesignFormat.DEF: Path(out_path)}, {}  # no metrics updates


Classic = Flow.factory.get("Classic")


@Flow.factory.register()
class FlowWithCustomAreaDoubler(Classic):
    Substitutions = {
        # Insert area doubler after floorplan
        "+OpenROAD.Floorplan": Step.factory.get("Example.AreaDoubler"),
        # Insert DEF to ODB after area doubler (update OpenROAD database)
        "+Example.AreaDoubler": Step.factory.get("OpenROAD.DEFtoODB"),
        # Replace XOR step with nothing because it will inevitably fail
        "KLayout.XOR": None,
    }
