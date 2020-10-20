import * as React from "react";
import {connect} from "react-redux";
import {Dropdown, Glyphicon, MenuItem} from "react-bootstrap";
import PropTypes from "prop-types";

class MenuAlert extends React.Component {
    render() {
        // provision status
        let provisioning = null
        if (this.props.status.provisioning.status) {
            provisioning = (
                <MenuItem href={this.props.status.provisioning.link}>
                    <Glyphicon glyph={'cog'}/>
                    {' '}Deployment in progress.
                </MenuItem>
            )
        }
        // users in change
        let usersInChange = null
        if (this.props.status.usersInChange.length > 0) {
            let users = []
            this.props.status.usersInChange.forEach((username) => {
                users.push(<li>{username}</li>)
            })
            usersInChange = []
            usersInChange.push(<b>These people are currently making a change:</b>)
            usersInChange.push(<ul>{users}</ul>)
        }

        if (provisioning !== null || usersInChange !== null) {
            return (
                <li className="dropdown" id="menu-alert-dropdown">
                    <a href="#"
                       style={{'background': '#f0ad4e', 'color': 'white'}}
                       className="dropdown-toggle"
                       aria-haspopup={true}
                       aria-expanded={false}
                       role="button"
                       data-toggle="dropdown">
                        <Glyphicon glyph={"warning-sign"}/>
                    </a>
                    <Dropdown.Menu>
                        {provisioning}
                        {usersInChange}
                    </Dropdown.Menu>
                </li>
            )
        }
        return (<li/>)
    }
}

MenuAlert.propTypes = {
    status: PropTypes.shape({
        provisioning: PropTypes.shape({
            status: PropTypes.bool,
            link: PropTypes.string,
        }),
        usersInChange: PropTypes.arrayOf(PropTypes.string),
    })
}

export default connect(
    (state) => ({
        status: state.globalStatus
    }),
)(MenuAlert)