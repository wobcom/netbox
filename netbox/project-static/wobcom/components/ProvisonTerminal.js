import * as React from "react";
import {Terminal} from "xterm";
import {FitAddon} from "xterm-addon-fit";
import {SearchAddon} from "xterm-addon-search";
import {WebLinksAddon} from "xterm-addon-web-links";
import {TerminalSearch} from "./ProvisionTerminalSearch";

export class ProvisionTerminal extends React.Component {
    constructor(props) {
        super(props);
        this.termRef = React.createRef()
        this.setupTerminal()
        this.terminal.write(props.initialContent)
        this.startWebsocket(props.provisonId)
    }

    setupTerminal() {
        this.terminal = new Terminal({
            rows: 50,
            scrollback: 1000000,
            theme: {
                selection: 'rgba(255, 124, 0, 0.5)',
            }
        })
        this.terminalFit = new FitAddon()
        this.terminal.loadAddon(this.terminalFit)
        this.terminalSearch = new SearchAddon()
        this.terminal.loadAddon(this.terminalSearch)
        this.terminal.loadAddon(new WebLinksAddon())
    }

    startWebsocket(provisionId) {
        let websocket = new WebSocket((location.protocol.startsWith('https') ? 'wss' : 'ws') + '://' + location.host + '/change/provisions/' + provisionId + '/logs/ws/');
        websocket.onmessage = (msg) => {
            var data = JSON.parse(msg.data);
            if (data.scope === 'default') {
                this.terminal.write(data.line.replace(/\n/g, '\r\n'));
            }
        };
    }

    componentDidMount() {
        this.terminal.open(this.termRef.current)
        this.terminalFit.fit()
    }

    render() {
        return (
            <div>
                <TerminalSearch search_addon={this.terminalSearch}/>
                <div ref={this.termRef}/>
            </div>
        )
    }
}
