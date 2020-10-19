import * as React from "react";
import {connect} from "react-redux";
import * as L from "partial.lenses";
import {Button, Glyphicon} from "react-bootstrap";
import PropTypes from "prop-types";


class ProvisionSecondStageButton extends React.Component {
    render() {
        return (
            <Button bsStyle={"warning"} disabled={!this.props.show} type={'submit'}>
                <Glyphicon glyph={"play"}/>
                {" "}Commit
            </Button>
        )
    }
}

ProvisionSecondStageButton.propTypes = {
    show: PropTypes.bool,
}

export default connect(
    (state) => ({
        show: L.get(L.compose(
            L.prop("provisionStatus"),
            L.prop("status"),
            L.prop("id"),
            L.valueOr(0)
        ), state) === 'reviewing'
    })
)(ProvisionSecondStageButton)