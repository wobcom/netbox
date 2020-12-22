import * as React from "react";
import {Terminal} from "xterm";
import {FitAddon} from "xterm-addon-fit";
import {WebLinksAddon} from "xterm-addon-web-links";
import {Button, Col, Panel} from "react-bootstrap";
import PropTypes from "prop-types";

export class ProvisionTerminal extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            fullscreen: false
        }
        this.termRef = React.createRef()
        this.setupTerminal()
        this.startWebsocket(props.provisionId)
        this.toggleFullscreen = this.toggleFullscreen.bind(this)
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

    toggleFullscreen() {
        this.setState({fullscreen:!this.state.fullscreen});
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
    }

    componentDidUpdate() {
        this.terminalFit.fit()
    }

    render() {

        let fullscreenIcon = (<i className={'mdi mdi-arrow-expand'} title={'Expand'}/>)
        let terminalSize = 8
        if (this.state.fullscreen) {
            fullscreenIcon = (<i className={'mdi mdi-arrow-collapse'} title={'Collapse'}/>)
            terminalSize = 12
        }

        return (
            <Col md={terminalSize}>
                <Panel>
                    <Panel.Heading>
                        <div className={'pull-right'}>
                            <Button bsSize="xsmall" onClick={this.toggleFullscreen}>
                                {fullscreenIcon}
                            </Button>
                        </div>
                        <strong>
                            Logs
                        </strong>
                    </Panel.Heading>
                    <Panel.Body style={{padding: 0}}>
                        <div ref={this.termRef}/>
                    </Panel.Body>
                </Panel>
            </Col>
        )
    }
}

ProvisionTerminal.propTypes = {
    provisionId: PropTypes.string,
}
