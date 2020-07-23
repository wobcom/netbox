import * as React from "react"
import * as ReactDOM from "react-dom"
import {ProvisionTerminal} from "./components/ProvisonTerminal"
import {ProvisionTimeout} from "./components/ProvisionTimeout";

window.React = React
window.ReactDOM = ReactDOM

window.ReactComponents = {
    ProvisionTerminal: ProvisionTerminal,
    ProvisionTimeout: ProvisionTimeout,
}
