from tsutils.menu.closable_embed_base import ClosableEmbedMenuBase

from padinfo.view.awakening_help import AwakeningHelpView
from padinfo.view.experience_curve import ExperienceCurveView
from padinfo.view.id_traceback import IdTracebackView


class ClosableEmbedMenu(ClosableEmbedMenuBase):
    view_types = {
        AwakeningHelpView.VIEW_TYPE: AwakeningHelpView,
        IdTracebackView.VIEW_TYPE: IdTracebackView,
        ExperienceCurveView.VIEW_TYPE: ExperienceCurveView,
    }
