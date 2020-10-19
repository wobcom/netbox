import * as React from "react";
import {Label} from "react-bootstrap";
import {connect} from "react-redux";
import PropTypes from "prop-types";

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
        if ("id" in this.props.status &&
            "str" in this.props.status) {
            return (
                <Label bsStyle={this.styleLookup(this.props.status.id)}>
                    {this.props.status.str}
                </Label>
            )
        }
        return null
    }
}

ProvisionSetStatus.propTypes = {
    status: PropTypes.shape({
        id: PropTypes.string,
        str: PropTypes.string,
    }),
}

export default connect(
    (state) => ({status: state.provisionStatus.status}),
)(ProvisionSetStatus)
