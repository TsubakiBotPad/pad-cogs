from .pipelineui import PipelineUI

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    pdb = PipelineUI(bot)
    bot.add_cog(pdb)
