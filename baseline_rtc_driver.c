#include "stm32f10x_rtc.h"
#include "stm32f10x_system.h"

int main(void) {
    // Enable the LSE clock
    RCC_LSECmd(RCC_LSE_ENABLE);

    // Wait for the LSE clock to be stable
    while (!(RCC_GetFlagStatus(RCC_LSERDY))) {}

    // Initialize the RTC
    RTC_InitTypeDef rtcInit;
    rtcInit.Asynchronous = FALSE;
    rtcInit.ClockSource = RTC_CLOCKSOURCE_LSE;
    RTC_Init(&rtcInit);

    // Set the RTC date and time
    RTC_SetTime(0x00, 0x01, 0x02, 0x03, 0x04); // year, month, day, hour, minute

    // Enable the RTC interrupt
    NVIC_EnableIRQ(RTC_IRQn);
    NVIC_SetPriority(RTC_IRQn, 5);

    // Set the RTC interrupt to occur every second
    RTC_SetAlarm(1, 0); // alarm at 00:00:01

    while (1) {
        // Wait for the RTC interrupt
        __WFI();
    }
}

void RTC_IRQHandler(void) {
    // Clear the RTC interrupt flag
    RTC_ClearIT(RTC_IT_ALARMA);

    // Handle the RTC interrupt here
    // For example, you can toggle an LED or send a message
}