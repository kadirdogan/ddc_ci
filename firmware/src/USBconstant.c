#include "USBconstant.h"

__code USB_Descriptor_Device_t DeviceDescriptor = {
    .Header = {.Size = sizeof(USB_Descriptor_Device_t), .Type = DTYPE_Device},
    .USBSpecification = VERSION_BCD(1, 1, 0),
    .Class    = 0x00,
    .SubClass = 0x00,
    .Protocol = 0x00,
    .Endpoint0Size    = DEFAULT_ENDP0_SIZE,
    .VendorID         = 0x1209,
    .ProductID        = 0xC55D,
    .ReleaseNumber    = VERSION_BCD(1, 0, 0),
    .ManufacturerStrIndex = 1,
    .ProductStrIndex      = 2,
    .SerialNumStrIndex    = 3,
    .NumberOfConfigurations = 1
};

__code USB_Descriptor_Configuration_t ConfigurationDescriptor = {
    .Config = {
        .Header = {.Size = sizeof(USB_Descriptor_Configuration_Header_t),
                   .Type = DTYPE_Configuration},
        .TotalConfigurationSize = sizeof(USB_Descriptor_Configuration_t),
        .TotalInterfaces        = 1,
        .ConfigurationNumber    = 1,
        .ConfigurationStrIndex  = NO_DESCRIPTOR,
        .ConfigAttributes       = USB_CONFIG_ATTR_RESERVED,
        .MaxPowerConsumption    = USB_CONFIG_POWER_MA(100)
    },

    .HID_Interface = {
        .Header = {.Size = sizeof(USB_Descriptor_Interface_t),
                   .Type = DTYPE_Interface},
        .InterfaceNumber  = 0,
        .AlternateSetting = 0,
        .TotalEndpoints   = 1,
        .Class    = HID_CSCP_HIDClass,
        .SubClass = HID_CSCP_NonBootSubclass,   // vendor HID, no boot
        .Protocol = HID_CSCP_NonBootProtocol,   // no specific protocol
        .InterfaceStrIndex = NO_DESCRIPTOR
    },

    .HID_KeyboardHID = {
        .Header = {.Size = sizeof(USB_HID_Descriptor_HID_t),
                   .Type = HID_DTYPE_HID},
        .HIDSpec               = VERSION_BCD(1, 1, 0),
        .CountryCode           = 0x00,
        .TotalReportDescriptors = 1,
        .HIDReportType         = HID_DTYPE_Report,
        .HIDReportLength       = sizeof(ReportDescriptor)
    },

    .HID_ReportINEndpoint = {
        .Header = {.Size = sizeof(USB_Descriptor_Endpoint_t),
                   .Type = DTYPE_Endpoint},
        .EndpointAddress = KEYBOARD_EPADDR,
        .Attributes      = (EP_TYPE_INTERRUPT | ENDPOINT_ATTR_NO_SYNC |
                            ENDPOINT_USAGE_DATA),
        .EndpointSize        = KEYBOARD_EPSIZE,
        .PollingIntervalMS   = 10
    }
};

// Vendor HID report descriptor: 2 byte input (brightness + contrast)
__code uint8_t ReportDescriptor[] = {
    0x06, 0x00, 0xFF,  // Usage Page (Vendor Defined 0xFF00)
    0x09, 0x01,        // Usage (Vendor Usage 1)
    0xA1, 0x01,        // Collection (Application)
    0x15, 0x00,        //   Logical Minimum (0)
    0x26, 0xFF, 0x00,  //   Logical Maximum (255)
    0x75, 0x08,        //   Report Size (8)
    0x95, 0x08,        //   Report Count (8)
    0x09, 0x02,        //   Usage (Vendor Usage 2)
    0x81, 0x02,        //   Input (Data, Variable, Absolute)
    0xC0               // End Collection
};

__code uint8_t LanguageDescriptor[] = {0x04, 0x03, 0x09, 0x04};

__code uint16_t SerialDescriptor[] = {
    (((3 + 1) * 2) | (DTYPE_String << 8)),
    '0', '0', '1'
};

__code uint16_t ProductDescriptor[] = {
    (((14 + 1) * 2) | (DTYPE_String << 8)),
    'P','O','T','-','C','o','n','t','r','o','l','l','e','r'
};

__code uint16_t ManufacturerDescriptor[] = {
    (((6 + 1) * 2) | (DTYPE_String << 8)),
    'D','e','q','i','n','g'
};
