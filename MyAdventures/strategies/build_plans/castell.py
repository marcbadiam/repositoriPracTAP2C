from .base_plan import BuildPlan


class CastellPlan(BuildPlan):
    @property
    def name(self):
        return "castell"

    @property
    def bom(self):
        return {"sandstone": 25, "stone": 45}

    def generate(self, x, y, z):
        return self.load_from_csv("castell.csv", x, y, z)
