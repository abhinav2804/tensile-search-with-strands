document.addEventListener("DOMContentLoaded", () => {
  const promptTextarea = document.getElementById("prompt-textarea")
  const submitButton = document.getElementById("submit-button")
  const responseArea = document.getElementById("response-area")
  const responseText = document.getElementById("response-text")
  const dynamicTextSpan = document.getElementById("dynamic-text")

  let prompt = ""
  let isGenerating = false

  // Dynamic Text Effect
  const phrases = ["Elastic Search", "Model Context Protocol", "AI Powered Search"]
  let phraseIndex = 0
  let charIndex = 0
  let isDeleting = false

  function typeEffect() {
    const currentPhrase = phrases[phraseIndex]
    const typingSpeed = 100
    const deletingSpeed = 50
    const delayBetweenPhrases = 1500

    if (!isDeleting) {
      if (charIndex < currentPhrase.length) {
        dynamicTextSpan.textContent += currentPhrase[charIndex]
        charIndex++
        setTimeout(typeEffect, typingSpeed)
      } else {
        setTimeout(() => {
          isDeleting = true
          typeEffect()
        }, delayBetweenPhrases)
      }
    } else {
      if (charIndex > 0) {
        dynamicTextSpan.textContent = currentPhrase.substring(0, charIndex - 1)
        charIndex--
        setTimeout(typeEffect, deletingSpeed)
      } else {
        isDeleting = false
        phraseIndex = (phraseIndex + 1) % phrases.length
        setTimeout(typeEffect, typingSpeed)
      }
    }
  }

  typeEffect() // Start the typing effect

  // Handle Prompt Submission
  promptTextarea.addEventListener("input", (e) => {
    prompt = e.target.value
    submitButton.disabled = isGenerating || !prompt.trim()
  })

  submitButton.addEventListener("click", async () => {
    if (isGenerating || !prompt.trim()) return

    isGenerating = true
    submitButton.textContent = "Generating..."
    submitButton.disabled = true
    promptTextarea.disabled = true
    responseArea.classList.add("hidden") // Hide previous response
    responseText.textContent = ""

    // Simulate an API call
    await new Promise((resolve) => setTimeout(resolve, 2000)) // Simulate network delay
    responseText.textContent = `Generating response for: "${prompt}"...`
    responseArea.classList.remove("hidden") // Show response area

    await new Promise((resolve) => setTimeout(resolve, 1500))
    responseText.textContent = `Here is a simulated response based on your prompt: "${prompt}". This demonstrates the power of ${dynamicTextSpan.textContent} in AI tools.`

    isGenerating = false
    submitButton.textContent = "Submit Prompt"
    submitButton.disabled = !prompt.trim()
    promptTextarea.disabled = false
  })
})
