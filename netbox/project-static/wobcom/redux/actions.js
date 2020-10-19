import {SET_GLOBAL_STATE, SET_PROVISIONING_STATE, SET_USERS_IN_CHANGE} from "./actionTypes";

export const setGlobalState = (state) => ({
    type: SET_GLOBAL_STATE,
    payload: state,
});

export const setUsersInChange = (state) => ({
    type: SET_USERS_IN_CHANGE,
    payload: state
})

export const setProvisioningStatus = (state) => ({
    type: SET_PROVISIONING_STATE,
    payload: state,
});