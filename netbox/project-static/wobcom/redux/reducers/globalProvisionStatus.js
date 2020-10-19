import * as L from "partial.lenses"
import {SET_GLOBAL_STATE, SET_USERS_IN_CHANGE} from "../actionTypes";

const initialState = {
    provisioning: {
        status: false,
        pk: null,
    },
    usersInChange: []
}

export default function (state=initialState, action) {
    switch (action.type) {
        case SET_GLOBAL_STATE:
            return L.set(
                L.prop("provisioning"),
                action.payload, state
            )
        case SET_USERS_IN_CHANGE:
            return L.set(
                L.prop("usersInChange"),
                action.payload, state
            )
        default:
            return state
    }
}
