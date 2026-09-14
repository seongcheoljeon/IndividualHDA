"""Asset table filtering with the shared null-safe predicate."""

from model.proxy_filters import AssetProxyModel
from model.ihda_table_model import TableModel


class TableProxyModel(AssetProxyModel):
    tag_role = TableModel.tag_role
    type_role = TableModel.type_role
    cate_role = TableModel.cate_role
    favorite_role = TableModel.favorite_role
    id_role = TableModel.id_role
