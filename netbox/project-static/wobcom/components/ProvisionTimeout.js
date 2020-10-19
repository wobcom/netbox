import * as React from "react";

export class ProvisionTimeout extends React.Component {
    constructor(props) {
        super(props);
        this.timerId = null
        this.timeOffset = Date.now() - props.timestamp
        this.state = {
            timeout: ""
        }
    }

    leadingZero(x) {
        if (x < 10) {
            return "0" + x
        }
        return x
    }

    recalculateTimeout(timeout, offset) {
        let remainingTime = timeout - (Date.now() - offset);
        if (remainingTime > 0) {
            let remainingDate = new Date(remainingTime)
            this.setState({
                timeout: [
                    this.leadingZero(remainingDate.getUTCHours()),
                    this.leadingZero(remainingDate.getUTCMinutes()),
                    this.leadingZero(remainingDate.getUTCSeconds()),
                ].join(":"),
            })
        } else {
            this.setState({timeout: "00:00"})
            clearInterval(this.timerId)
        }
    }

    componentDidMount() {
        this.recalculateTimeout()
        this.timerId = setInterval(() => {
            this.recalculateTimeout(this.props.timeout, this.timeOffset)
        }, 500)
    }

    componentWillUnmount() {
        clearInterval(this.timerId)
    }

    render() {
        return this.state.timeout
    }
}