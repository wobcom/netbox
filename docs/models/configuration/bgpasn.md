# ASN

ASNs (Autonomous System Numbers) are numbers assigned to autonomous systems,
which are entities that operate networks. Their numbers are their primary
identifier, allocated by IANA or RIRs (regional Internet registries).

In the context of Netbox and BGP, we use the ASN to decide which networks to
expose to which operator. These ASNs can then be placed on devices.

We also provide the option “redistribute connected”, which maps to the CISCO
command `redistribute connected`. It tells the device to redistribute routes
between routing domains (“connected” refers to routes that are automatically
established by enabling IP). Since this can be managed on a per-ASN basis on
CISCO, we mirror this behavior.
