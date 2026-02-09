#include "stm32f10x_usart.h"
#include "stm32f10x_rcc.h"

int main(void) {
    // Enable HSE clock (8MHz)
    RCC_HSE_BypassCmd(ENABLE);
    while (!RCC_HSE_IsReady()) {}

    // Configure USART1
    USART_InitTypeDef usart_init;
    usart_init.USART_BaudRate = 9600;
    usart_init.USART_WordLength = USART_WordLength_8b;
    usart_init.USART_StopBits = USART_StopBits_1;
    usart_init.USART_Parity = USART_Parity_None;
    usart_init.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;

    // Enable RX interrupt with echo-back
    USART_ITConfig(USART1, USART_IT_RXNE);
    NVIC_EnableIRQ(USART1_IRQn);

    // Start USART1
    USART_Cmd(USART1, ENABLE);

    while (1) {
        // Wait for data reception
        while (!(USART_GetITStatus(USART1, USART_IT_RXNE))) {}
        // Read received data and echo it back
        uint8_t data = USART_ReceiveData(USART1);
        USART_SendData(USART1, data);
    }
}