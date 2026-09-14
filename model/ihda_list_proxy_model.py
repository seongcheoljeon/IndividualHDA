"""Asset list filtering with the shared null-safe predicate."""

from model.proxy_filters import AssetProxyModel
from model.ihda_list_model import ListModel


class ListProxyModel(AssetProxyModel):
    tag_role = ListModel.tag_role
    type_role = ListModel.type_role
    cate_role = ListModel.cate_role
    favorite_role = ListModel.favorite_role
    id_role = ListModel.id_role
