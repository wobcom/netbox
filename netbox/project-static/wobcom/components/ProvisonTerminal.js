import * as React from "react";
import {Terminal} from "xterm";
import {FitAddon} from "xterm-addon-fit";
import {WebLinksAddon} from "xterm-addon-web-links";

import PropTypes from "prop-types";

export class ProvisionTerminal extends React.Component {
    constructor(props) {
        super(props);
        this.termRef = React.createRef()
        this.setupTerminal()
        this.startWebsocket(props.provisionId)
    }

    setupTerminal() {
        this.terminal = new Terminal({
            rows: 50,
            disableStdin: true,
            scrollback: 1000000,
            rendererType: "dom",
            convertEol: true,
            theme: {
                selection: 'rgba(255, 124, 0, 0.5)',
            }
        })
        this.terminalFit = new FitAddon()
        this.terminal.loadAddon(this.terminalFit)
        this.terminal.loadAddon(new WebLinksAddon())
    }

    startWebsocket(provisionId) {
        let path = '/ws/change/provisions/' + provisionId + '/logs/';
        let url = new URL(path, window.location.href);
        url.protocol = url.protocol.replace('http', 'ws');

        let websocket = new WebSocket(url);
        websocket.onmessage = (msg) => {
            const data = msg.data;
            if (typeof data === 'string') {
                this.terminal.write(data);
            } else {
                let reader = new FileReader()
                reader.addEventListener('loadend', () => {
                    this.terminal.write(reader.result)
                })
                reader.readAsBinaryString(data)
            }
        };
    }

    componentDidMount() {
        this.terminal.open(this.termRef.current)
        this.terminalFit.fit()
    }

    render() {
        return (
            <div ref={this.termRef}/>
        )
    }
}

ProvisionTerminal.propTypes = {
    provisionId: PropTypes.number,
}
