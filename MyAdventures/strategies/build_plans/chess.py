from .base_plan import BuildPlan


class ChessPlan(BuildPlan):
    @property
    def name(self):
        return "chess"

    @property
    def bom(self):
        return {"stone": 18, "dirt": 18}

    def generate(self, x, y, z):
        return self.load_from_csv("chess.csv", x, y, z)
