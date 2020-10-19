import * as React from "react"
import * as ReactDOM from "react-dom"
import {Provider} from "react-redux";
import MenuAlert from "./components/MenuAlert";
import ProvisionSetStatus from "./components/ProvisionSetStatus";
import ProvisionSecondStageButton from "./components/ProvisionSecondStageButton";
import ProvisionTerminateButton from "./components/ProvisionTerminateButton";
import {ProvisionTerminal} from "./components/ProvisonTerminal"
import store from "./redux/store"
import {setGlobalState, setProvisioningStatus, setUsersInChange} from "./redux/actions";

/*
Creates websocket url from location data and path.
 */
let wsAddress = (path) => {
    return (location.protocol.startsWith('https') ? 'wss' : 'ws') + '://' + location.host + path
}

/*
Creates Websocket trying to reconnect after timeout.
 */
let reconnectingWS = (address, messageCallback=()=>{}, timeout=2000) => {
    let initWS = () => {
        let ws = new WebSocket(address)

        ws.onmessage = messageCallback

        ws.onclose = () => {
            console.error("Websocket closed \""+address+"\" trying to reconnect in " + timeout +"ms")
            setTimeout(initWS, timeout)
        }
    }

    initWS()
}

reconnectingWS(wsAddress('/ws/change/provisions/status/'), (msg) => {
    let data = JSON.parse(msg.data)
    store.dispatch(setGlobalState(data))
})

reconnectingWS(wsAddress('/ws/change/active_users/'), (msg) => {
    let data = JSON.parse(msg.data)
    store.dispatch(setUsersInChange(data))
})


window.React = React
window.ReactDOM = ReactDOM

window.ReactComponents = {
    ProvisionTerminal: ProvisionTerminal,
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll(".provision-set-label").forEach((elem) => {
        ReactDOM.render(<Provider store={store}><ProvisionSetStatus/></Provider>, elem)
    })

    document.querySelectorAll(".btn-second-stage").forEach((elem) => {
        ReactDOM.render(<Provider store={store}><ProvisionSecondStageButton/></Provider>, elem)
    })

    document.querySelectorAll(".btn-terminate").forEach((elem) => {
        ReactDOM.render(<Provider store={store}><ProvisionTerminateButton form={elem.dataset.form} /></Provider>, elem)
    })

    document.querySelectorAll('#provision-status-ws').forEach((elem) => {
        const id = elem.dataset.provisionId
        if (id === undefined) {
            console.error("Missing \"data-provision-id\" for connecting websocket.")
            return
        }
        reconnectingWS(
            wsAddress('/ws/change/provisions/' + id + '/status/'),
            (msg) => {
                store.dispatch(setProvisioningStatus(JSON.parse(msg.data)))
            }
        )
    })

    document.querySelectorAll('#menu-alert').forEach((elem) => {
        const div = document.createElement('div')
        ReactDOM.render(<Provider store={store}><MenuAlert/></Provider>, div)
        elem.parentElement.replaceChild(div.childNodes[0], elem)
    })
})
