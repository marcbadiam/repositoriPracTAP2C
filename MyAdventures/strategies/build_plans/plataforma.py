from .base_plan import BuildPlan

class PlataformaPlan(BuildPlan):
    @property
    def name(self):
        return "plataforma"

    @property
    def bom(self):
        return {"dirt": 8, "stone": 8}

    def generate(self, x, y, z):
        plan = []
        platform_y = y + 1
        for dx in range(4):
            for dz in range(4):
                material = "dirt" if dx < 2 else "stone"
                plan.append((x + dx, platform_y, z + dz, material))
        return plan
