import {SET_PROVISIONING_STATE} from "../actionTypes";

const initialState = {
    status: {}
}

export default function (state=initialState, action) {
    switch (action.type) {
        case SET_PROVISIONING_STATE:
            return action.payload
        default:
            return state
    }
}
