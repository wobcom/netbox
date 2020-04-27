# Route maps

Route maps are a way of filtering BGP routing updates. You can use them to
tell your BGP routing configuration to not advertise some networks.

Because route maps are complicated and highly configurable, they are mostly
opaque to Netbox. They only have a name and a configuration associated with it.
The configuration will be passed through to your device directly.
