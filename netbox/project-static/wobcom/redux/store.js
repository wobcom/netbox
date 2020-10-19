import {createStore, combineReducers} from "redux"
import setGlobalState from "./reducers/globalProvisionStatus"
import setProvisionState from "./reducers/provisioningStatus"

export default createStore(
    combineReducers({
        globalStatus: setGlobalState,
        provisionStatus: setProvisionState,
    }),
    window.__REDUX_DEVTOOLS_EXTENSION__ && window.__REDUX_DEVTOOLS_EXTENSION__()
)