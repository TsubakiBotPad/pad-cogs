from .padvision import PadVision, NeuralClassifierBoardExtractor

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    bot.add_cog(PadVision(bot))
