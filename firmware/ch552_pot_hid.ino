// ch552_pot_hid.ino
// Tools -> USB Settings -> USER CODE w/ 148B USB ram

#include "src/include/ch5xx.h"
#include "src/include/ch5xx_usb.h"
#include "src/USBconstant.h"
#include "src/USBhandler.h"

#define PIN_LED 30  // P3.0

extern uint8_t USB_EP1_send();
extern __xdata uint8_t HIDKey[];
extern volatile __xdata uint8_t UsbConfig;

uint8_t adc_read_ch(uint8_t chan) {
    ADC_CHAN1 = (chan >> 1) & 1;
    ADC_CHAN0 = (chan >> 0) & 1;
    ADC_START = 1;
    while (ADC_START);
    return ADC_DATA;
}

void led_blink(uint8_t count) {
    for (__data uint8_t i = 0; i < count; i++) {
        digitalWrite(PIN_LED, HIGH);
        delay(100);
        digitalWrite(PIN_LED, LOW);
        delay(100);
    }
}

void setup() {
    ADC_CFG = bADC_EN | bADC_CLK;
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, LOW);

    // D+ pull-up'i kapat - Windows cihazin ciktigini gorur
    USB_CTRL = 0x00;
    UDEV_CTRL = bUD_PD_DIS;  // pull-down disable, pull-up kapali
    delay(500);              // Windows'un disconnect'i algilamasi icin bekle

    // Normal USB init - D+ pull-up acilir, Windows yeniden enumerate eder
    USBInit();

    // Enumerate tamamlanana kadar bekle (max 5 saniye)
    __data uint16_t wait = 0;
    while (UsbConfig == 0 && wait < 5000) {
        delay(1);
        wait++;
    }

    if (UsbConfig != 0) {
        led_blink(3);  // enumerate OK
    } else {
        led_blink(1);  // enumerate basarisiz
    }
}

void loop() {
    static uint8_t last_b = 255, last_c = 255;
    static uint8_t sent_b = 255, sent_c = 255;

    uint8_t b = adc_read_ch(0);  // P1.1
    uint8_t c = adc_read_ch(1);  // P1.4

    // ±1 raw jitter'i yoksay
    if (b > last_b + 1 || b + 1 < last_b) last_b = b;
    if (c > last_c + 1 || c + 1 < last_c) last_c = c;

    // Sadece değer değiştiğinde gönder
    if (last_b != sent_b || last_c != sent_c) {
        sent_b = last_b;
        sent_c = last_c;
        HIDKey[0] = sent_b;
        HIDKey[1] = sent_c;
        USB_EP1_send();
    }

    delay(50);
}
