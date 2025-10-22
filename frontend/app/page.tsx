"use client"

import { useState, useEffect } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"

export default function HomePage() {
  const [prompt, setPrompt] = useState("")
  const [response, setResponse] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [dynamicText, setDynamicText] = useState("")
  const phrases = ["Elastic Search", "Model Context Protocol", "AI Powered Search"]
  const [phraseIndex, setPhraseIndex] = useState(0)
  const [charIndex, setCharIndex] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    const typingSpeed = 100
    const deletingSpeed = 50
    const delayBetweenPhrases = 1500

    let timer: NodeJS.Timeout

    const handleTyping = () => {
      const currentPhrase = phrases[phraseIndex]
      if (!isDeleting) {
        if (charIndex < currentPhrase.length) {
          setDynamicText((prev) => prev + currentPhrase[charIndex])
          setCharIndex((prev) => prev + 1)
          timer = setTimeout(handleTyping, typingSpeed)
        } else {
          timer = setTimeout(() => setIsDeleting(true), delayBetweenPhrases)
        }
      } else {
        if (charIndex > 0) {
          setDynamicText((prev) => prev.slice(0, prev.length - 1))
          setCharIndex((prev) => prev - 1)
          timer = setTimeout(handleTyping, deletingSpeed)
        } else {
          setIsDeleting(false)
          setPhraseIndex((prev) => (prev + 1) % phrases.length)
          timer = setTimeout(handleTyping, typingSpeed)
        }
      }
    }

    timer = setTimeout(handleTyping, typingSpeed)

    return () => clearTimeout(timer)
  }, [charIndex, isDeleting, phraseIndex, phrases])

  const handleSubmit = async () => {
    setIsGenerating(true)
    setResponse("") // Clear previous response
    // Simulate an API call
    await new Promise((resolve) => setTimeout(resolve, 2000)) // Simulate network delay
    setResponse(`Generating response for: "${prompt}"...`)
    await new Promise((resolve) => setTimeout(resolve, 1500))
    setResponse(
      `Here is a simulated response based on your prompt: "${prompt}". This demonstrates the power of ${dynamicText} in AI tools.`,
    )
    setIsGenerating(false)
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-gray-900 to-blue-950 flex items-center justify-center p-4">
      {/* Animated background blob shapes - Increased visibility */}
      <div
        className="absolute top-1/4 left-1/4 w-64 h-64 bg-purple-500 rounded-full opacity-70 animate-blob"
        style={{ animationDelay: "2s" }}
      ></div>
      <div
        className="absolute top-1/2 right-1/4 w-72 h-72 bg-indigo-500 rounded-full opacity-70 animate-blob"
        style={{ animationDelay: "4s" }}
      ></div>
      <div
        className="absolute bottom-1/4 left-1/3 w-56 h-56 bg-pink-500 rounded-full opacity-70 animate-blob"
        style={{ animationDelay: "0s" }}
      ></div>

      <div className="relative z-10 w-full max-w-2xl bg-gray-800 rounded-xl shadow-2xl p-8 space-y-6 border border-gray-700 transform transition-all duration-500 hover:scale-[1.005] hover:shadow-3xl">
        <h1 className="text-4xl font-extrabold text-center text-gray-100 bg-clip-text text-transparent bg-gradient-to-r from-cyan-300 to-fuchsia-300">
          Elastic Search Prompt Interface
        </h1>

        <div className="text-center text-lg font-medium text-gray-300">
          <span className="text-indigo-300 font-semibold">{dynamicText}</span>
          <span className="animate-pulse text-indigo-300">|</span>
        </div>

        <div className="relative">
          <Textarea
            placeholder="Ask Anything..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-[120px] p-4 text-lg border-2 border-gray-600 focus:border-blue-400 focus:ring-4 focus:ring-blue-700 focus:ring-opacity-50 transition-all duration-300 resize-none bg-gray-700 text-gray-100 rounded-xl"
            disabled={isGenerating}
          />
          <Button
            onClick={handleSubmit}
            className="w-full mt-4 py-3 text-lg font-semibold bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 transition-all duration-300 text-white shadow-lg transform hover:scale-[1.01]"
            disabled={isGenerating || !prompt.trim()}
          >
            {isGenerating ? "Generating..." : "Submit Prompt"}
          </Button>
        </div>

        {response && (
          <div className="bg-gray-700 p-6 rounded-lg border border-gray-600 shadow-inner animate-fade-in">
            <h2 className="text-xl font-semibold text-gray-200 mb-3">AI Response:</h2>
            <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">{response}</p>
          </div>
        )}
      </div>
    </div>
  )
}
