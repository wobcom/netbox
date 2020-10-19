import * as React from "react";
import {connect} from "react-redux";
import * as L from "partial.lenses";
import {Button, Glyphicon, Modal} from "react-bootstrap";


class ProvisionTerminateButton extends React.Component {
    constructor(props) {
        super(props);
        this.showModal = this.showModal.bind(this)
        this.hideModal = this.hideModal.bind(this)
        this.state = {
            showModal: false
        }
    }

    showModal() {
        this.setState({showModal: true})
    }

    hideModal() {
        this.setState({showModal: false})
    }

    render() {
        return (
            <span>
                <Button bsStyle={"danger"} disabled={!this.props.show} onClick={this.showModal}>
                    <Glyphicon glyph={"ban-circle"}/>
                    {" "}Terminate
                </Button>
                <Modal show={this.state.showModal} onHide={this.hideModal}>
                    <Modal.Header closeButton>
                        <h4>Terminate Provisioning</h4>
                    </Modal.Header>
                    <Modal.Body>
                        Do you really want to terminate this provisioning?
                    </Modal.Body>
                    <Modal.Footer>
                        <Button onClick={this.hideModal}>Cancel</Button>
                        <Button bsStyle={"danger"} type={"submit"} form={this.props.form}>Terminate</Button>
                    </Modal.Footer>
                </Modal>
            </span>
        )
    }
}

export default connect(
    (state) => ({
        show: ['running', 'prepare', 'commit', 'reviewing'].indexOf(
            L.get(L.compose(
                L.prop("provisionStatus"),
                L.prop("status"),
                L.prop("id"),
                L.valueOr(0)
            ), state)) > 0
    })
)(ProvisionTerminateButton)