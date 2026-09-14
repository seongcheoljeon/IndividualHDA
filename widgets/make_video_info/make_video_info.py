from __future__ import annotations

from typing import Any

from PySide6 import QtWidgets

import public

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.17 21:09:45
# modified date:
# description:
from widgets.make_video_info import make_video_info_ui


class MakeVideoInfo(QtWidgets.QDialog, make_video_info_ui.Ui_Dialog__makevideoinfo):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.__sf = 1001
        self.__ef = 1240
        self.__fps = 24
        self.__res_dat = dict(
            zip(
                [
                    public.Key.Resolution.sd,
                    public.Key.Resolution.hd,
                    public.Key.Resolution.fhd,
                    public.Key.Resolution.qhd,
                ],
                [
                    public.Value.SD_res,
                    public.Value.HD_res,
                    public.Value.FHD_res,
                    public.Value.QHD_res,
                ],
            )
        )
        self.__res_dat_share = dict(
            zip(
                [
                    public.Key.Resolution.sd,
                    public.Key.Resolution.hd,
                    public.Key.Resolution.fhd,
                ],
                [public.Value.SD_res, public.Value.HD_res, public.Value.FHD_res],
            )
        )
        self.__init_set()
        self.__connections()

    def __init_set(self) -> None:
        # hide
        self.groupBox__share.setVisible(False)
        self.buttonBox__confirm.button(QtWidgets.QDialogButtonBox.Ok).setToolTip(
            "Start Make Video"
        )
        self.buttonBox__confirm.button(QtWidgets.QDialogButtonBox.Ok).setStatusTip(
            "Start Make Video"
        )
        self.buttonBox__confirm.button(QtWidgets.QDialogButtonBox.Cancel).setToolTip(
            "Cancel Make Video"
        )
        self.buttonBox__confirm.button(QtWidgets.QDialogButtonBox.Cancel).setStatusTip(
            "Cancel Make Video"
        )
        self.spinBox__sf.setValue(self.sf)
        self.spinBox__ef.setValue(self.ef)
        self.spinBox__fps.setValue(self.fps)
        self.comboBox__resolution.addItems(list(self.__res_dat.keys()))
        self.comboBox__resolution.setCurrentText(public.Key.Resolution.hd)
        self.comboBox__resolution_share.addItems(list(self.__res_dat_share.keys()))
        self.comboBox__resolution_share.setCurrentText(public.Key.Resolution.sd)
        self.__slot_confirm_resolution()
        self.__slot_confirm_resolution_share()

    def __connections(self) -> None:
        self.spinBox__sf.valueChanged.connect(self.__slot_sf)
        self.spinBox__ef.valueChanged.connect(self.__slot_ef)
        self.spinBox__fps.valueChanged.connect(self.__slot_fps)
        self.comboBox__resolution.currentTextChanged.connect(
            self.__slot_confirm_resolution
        )
        self.comboBox__resolution_share.currentTextChanged.connect(
            self.__slot_confirm_resolution_share
        )

    def __slot_confirm_resolution(self, *args: Any) -> None:
        self.label__confirm_resolution.setText(
            " x ".join([str(x) for x in self.get_resolution()])
        )

    def __slot_confirm_resolution_share(self, *args: Any) -> None:
        self.label__confirm_resolution_share.setText(
            " x ".join([str(x) for x in self.get_resolution_share()])
        )

    def get_resolution(self) -> list[int] | None:
        return self.__res_dat.get(self.comboBox__resolution.currentText())

    def get_resolution_share(self) -> list[int] | None:
        return self.__res_dat_share.get(self.comboBox__resolution_share.currentText())

    def __slot_sf(self, *args: Any) -> None:
        self.sf = args[0]

    def __slot_ef(self, *args: Any) -> None:
        self.ef = args[0]

    def __slot_fps(self, *args: Any) -> None:
        self.fps = args[0]

    @property
    def sf(self) -> int:
        return self.__sf

    @sf.setter
    def sf(self, val: Any) -> None:
        self.__sf = int(val)
        self.spinBox__sf.setValue(int(val))

    @property
    def ef(self) -> int:
        return self.__ef

    @ef.setter
    def ef(self, val: Any) -> None:
        self.__ef = int(val)
        self.spinBox__ef.setValue(int(val))

    @property
    def fps(self) -> float:
        return self.__fps

    @fps.setter
    def fps(self, val: Any) -> None:
        self.__fps = val
        self.spinBox__fps.blockSignals(True)
        self.spinBox__fps.setValue(round(val))
        self.spinBox__fps.blockSignals(False)

    @property
    def is_beautypass(self) -> bool:
        return self.checkBox__beautypassonly.isChecked()

    @property
    def is_init_sim(self) -> bool:
        return self.checkBox__initialize_sim.isChecked()

    @property
    def is_motionblur(self) -> bool:
        return self.checkBox__use_motionblur.isChecked()

    @property
    def is_crop_mask(self) -> bool:
        return self.checkBox__crop_out_mask_overlay.isChecked()

    @property
    def is_share_youtube(self) -> bool:
        return self.checkBox__youtube.isChecked()

    @property
    def is_share_vimeo(self) -> bool:
        return self.checkBox__vimeo.isChecked()
