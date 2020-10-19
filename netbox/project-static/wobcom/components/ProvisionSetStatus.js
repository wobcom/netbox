import * as React from "react";
import {Label} from "react-bootstrap";
import {connect} from "react-redux";
import * as L from "partial.lenses"

class ProvisionSetStatus extends React.Component {

    styleLookup(x) {
        switch (x) {
            case "not_started": return "primary"
            case "running": return "info"
            case "prepare": return "info"
            case "commit": return "info"
            case "finished": return "success"
            case "failed": return "danger"
            case "aborted": return "warning"
            case "reviewing": return "primary"
        }
    }

    render() {
        if (this.props.status.hasOwnProperty("id") &&
            this.props.status.hasOwnProperty("str")) {
            return (
                <Label bsStyle={this.styleLookup(this.props.status.id)}>
                    {this.props.status.str}
                </Label>
            )
        }
        return null
    }
}

export default connect(
    (state) => ({status: state.provisionStatus.status}),
)(ProvisionSetStatus)
