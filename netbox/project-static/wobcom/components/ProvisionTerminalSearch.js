import * as React from "react";
import {Button, ButtonGroup, Form, FormControl, FormGroup, Glyphicon} from "react-bootstrap";

export class TerminalSearch extends React.Component {
    constructor(props) {
        super(props);
        this.state = {text: '', found: undefined};
        this.search = this.search.bind(this);
        this.inputChange = this.inputChange.bind(this);
        this.searchPrevious = this.searchPrevious.bind(this);
    }

    search(e) {
        e.preventDefault();
        if (this.state.text !== "") {
            let found = this.props.search_addon.findNext(this.state.text, {caseSensitive: false});
            this.setState({found: found});
        }
    }

    searchPrevious() {
        if (this.state.text !== "") {
            let found = this.props.search_addon.findPrevious(this.state.text, {caseSensitive: false});
            this.setState({found: found});
        }
    }

    inputChange(e) {
        this.setState({text: e.target.value, found: undefined});
    }

    render() {

        let validationState = null,
            errorText = '',
            buttons;

        if (this.state.found !== undefined && !this.state.found) {
            validationState = 'error';
            errorText = 'No matches.';
        }
        if (this.state.found === undefined || !this.state.found) {
            buttons = (
                <Button type="submit" className="pull-right" bsStyle="primary">
                    <Glyphicon glyph="search"/>
                    Search
                </Button>
            )
        } else {
            buttons = (
                <ButtonGroup className="pull-right">
                    <Button type="submit" bsStyle="primary">
                        <Glyphicon glyph="arrow-down"/>
                        Next
                    </Button>
                    <Button type="submit" bsStyle="primary" onClick={this.searchPrevious}>
                        <Glyphicon glyph="arrow-up"/>
                        Previous
                    </Button>
                </ButtonGroup>
            )
        }

        return (
            <Form inline={true} onSubmit={this.search} style={{padding: "10px"}}>
                <FormGroup validationState={validationState}>
                    <FormControl
                        placeholder="Search"
                        value={this.state.text}
                        onChange={this.inputChange}
                    />
                </FormGroup>
                <FormGroup>
                    <p className="form-control-static" style={{marginLeft: "10px"}}>
                        {errorText}
                    </p>
                </FormGroup>
                {buttons}
            </Form>
        )
    }
}
