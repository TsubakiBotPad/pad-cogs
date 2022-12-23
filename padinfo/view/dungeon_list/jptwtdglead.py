from padinfo.view.dungeon_list.jpytdglead import JpYtDgLeadProps, JpYtDgLeadView

class JpTwtDgLeadProps(JpYtDgLeadProps):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class JpTwtDgLeadView(JpYtDgLeadView):
    VIEW_TYPE = 'JpTwtDgLead'
    dungeon_link = 'https://twitter.com/search?q={}%20{}&src=typed_query'
    subdungeon_link = 'https://twitter.com/search?q={}%20{}&src=typed_query'
