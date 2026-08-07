from dataclasses import dataclass
from typing import Optional, Callable

OSC_ADDRESS = {
    "track_volume":       "/track/{n}/volume",
    "track_pan":          "/track/{n}/pan",
    "track_mute":         "/track/{n}/mute",
    "track_solo":         "/track/{n}/solo",
    "track_recarm":       "/track/{n}/recarm",
    "track_select":       "/track/{n}/select",
    "fx_bypass":          "/track/{n}/fx/{k}/bypass",
    "fx_wetdry":          "/track/{n}/fx/{k}/wetdry",
    "fx_param_value":     "/track/{n}/fx/{k}/fxparam/{p}/value",
    "fx_open":            "/track/{n}/fx/{k}/open",
    "send_volume":        "/track/{n}/send/{k}/volume",
    "send_pan":           "/track/{n}/send/{k}/pan",
    "send_mute":          "/track/{n}/send/{k}/mute",
    "transport_play":     "/play",
    "transport_stop":     "/stop",
    "transport_record":   "/record",
    "transport_pause":    "/pause",
    "transport_repeat":   "/repeat",
    "transport_rewind":   "/rewind",
    "transport_forward":  "/forward",
    "tempo":              "/tempo",
    "time_position":      "/time",
    "action":             "/action",
    "action_str":         "/action/str",
}

INCOMING_ADDRESS = {
    "display_message":    "/nova/display/message",
    "mode_set":           "/nova/mode/set",
    "track_vu":           "/nova/track/{n}/vu",
    "master_vu":          "/nova/master/vu",
    "beat_position":      "/nova/beat",
    "play_state":         "/nova/play_state",
    "tuner":              "/nova/tuner",
}
