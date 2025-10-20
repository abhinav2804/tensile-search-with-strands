import React, { useState } from 'react';
import { Database, Cloud, Search, FileText, Zap, ArrowRight, CheckCircle, AlertCircle } from 'lucide-react';

const GenerativeIndexingDiagrams = () => {
  const [activeTab, setActiveTab] = useState('architecture');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            Generative Indexing System
          </h1>
          <p className="text-blue-200">AI-Powered Document Processing & Search Architecture</p>
        </div>

        {/* Tab Switcher */}
        <div className="flex justify-center gap-4 mb-8">
          <button
            onClick={() => setActiveTab('architecture')}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              activeTab === 'architecture'
                ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/50'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Architecture Diagram
          </button>
          <button
            onClick={() => setActiveTab('flow')}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              activeTab === 'flow'
                ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/50'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Processing Flow
          </button>
        </div>

        {/* Architecture Diagram */}
        {activeTab === 'architecture' && (
          <div className="bg-slate-800/50 backdrop-blur rounded-2xl p-8 shadow-2xl border border-slate-700">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Cloud className="text-blue-400" />
              System Architecture
            </h2>
            
            <div className="relative">
              {/* Input Layer */}
              <div className="flex justify-center mb-12">
                <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl p-6 shadow-lg">
                  <FileText className="w-8 h-8 text-white mb-2 mx-auto" />
                  <div className="text-white font-semibold text-center">Input Data</div>
                  <div className="text-green-100 text-sm text-center mt-1">
                    JSON, JSONL, CSV, TXT
                  </div>
                </div>
              </div>

              <div className="flex justify-center mb-12">
                <ArrowRight className="text-blue-400 rotate-90" size={32} />
              </div>

              {/* Core Layer - FastAPI */}
              <div className="flex justify-center mb-12">
                <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-8 shadow-lg max-w-sm">
                  <Zap className="w-10 h-10 text-white mb-3 mx-auto" />
                  <div className="text-white font-bold text-xl text-center mb-2">FastAPI Service</div>
                  <div className="text-blue-100 text-sm text-center">
                    • Real-time SSE Updates<br/>
                    • Multi-format Support<br/>
                    • Pipeline Orchestration
                  </div>
                </div>
              </div>

              <div className="flex justify-center mb-12">
                <ArrowRight className="text-blue-400 rotate-90" size={32} />
              </div>

              {/* Service Layer */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                {/* DynamoDB */}
                <div className="bg-gradient-to-br from-orange-500 to-red-600 rounded-xl p-6 shadow-lg">
                  <Database className="w-8 h-8 text-white mb-3 mx-auto" />
                  <div className="text-white font-semibold text-center mb-2">DynamoDB</div>
                  <div className="text-orange-100 text-sm text-center">
                    User Metadata Fetch
                  </div>
                </div>

                {/* AWS Bedrock */}
                <div className="bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl p-6 shadow-lg">
                  <Cloud className="w-8 h-8 text-white mb-3 mx-auto" />
                  <div className="text-white font-semibold text-center mb-2">AWS Bedrock</div>
                  <div className="text-purple-100 text-sm text-center">
                    AI Enhancement<br/>
                    Anthropic Models
                  </div>
                </div>

                {/* Document Processing */}
                <div className="bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl p-6 shadow-lg">
                  <FileText className="w-8 h-8 text-white mb-3 mx-auto" />
                  <div className="text-white font-semibold text-center mb-2">Processing</div>
                  <div className="text-cyan-100 text-sm text-center">
                    Smart Chunking<br/>
                    Schema Validation
                  </div>
                </div>
              </div>

              <div className="flex justify-center mb-12">
                <ArrowRight className="text-blue-400 rotate-90" size={32} />
              </div>

              {/* Output Layer */}
              <div className="flex justify-center">
                <div className="bg-gradient-to-br from-yellow-500 to-orange-600 rounded-xl p-6 shadow-lg">
                  <Search className="w-8 h-8 text-white mb-2 mx-auto" />
                  <div className="text-white font-semibold text-center">Elasticsearch</div>
                  <div className="text-yellow-100 text-sm text-center mt-1">
                    Searchable Index<br/>
                    Bulk Processing
                  </div>
                </div>
              </div>
            </div>

            {/* Technology Stack */}
            <div className="mt-12 pt-8 border-t border-slate-700">
              <h3 className="text-xl font-semibold text-white mb-4">Technology Stack</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-700/50 rounded-lg p-4 text-center">
                  <div className="text-blue-400 font-semibold">FastAPI</div>
                  <div className="text-slate-300 text-sm">Web Framework</div>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-4 text-center">
                  <div className="text-orange-400 font-semibold">AWS SDK</div>
                  <div className="text-slate-300 text-sm">Boto3</div>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-4 text-center">
                  <div className="text-yellow-400 font-semibold">Elasticsearch</div>
                  <div className="text-slate-300 text-sm">Search Engine</div>
                </div>
                <div className="bg-slate-700/50 rounded-lg p-4 text-center">
                  <div className="text-green-400 font-semibold">Python 3.10+</div>
                  <div className="text-slate-300 text-sm">Runtime</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Processing Flow */}
        {activeTab === 'flow' && (
          <div className="bg-slate-800/50 backdrop-blur rounded-2xl p-8 shadow-2xl border border-slate-700">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Zap className="text-blue-400" />
              Processing Pipeline Flow
            </h2>

            <div className="space-y-6">
              {/* Step 1 */}
              <div className="flex items-start gap-4">
                <div className="bg-blue-500 rounded-full w-12 h-12 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <span className="text-white font-bold text-xl">1</span>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="text-green-400" size={20} />
                    <h3 className="text-white font-semibold text-lg">API Request Received</h3>
                  </div>
                  <p className="text-slate-300 mb-2">
                    GET /triggerIndexingLive endpoint receives request with parameters
                  </p>
                  <div className="bg-slate-800 rounded p-3 font-mono text-sm text-blue-300">
                    user_id, data_path, user_query_path
                  </div>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <ArrowRight className="text-blue-400 rotate-90" size={28} />
              </div>

              {/* Step 2 */}
              <div className="flex items-start gap-4">
                <div className="bg-orange-500 rounded-full w-12 h-12 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <span className="text-white font-bold text-xl">2</span>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Database className="text-orange-400" size={20} />
                    <h3 className="text-white font-semibold text-lg">Fetch User Metadata</h3>
                  </div>
                  <p className="text-slate-300">
                    Query DynamoDB to retrieve user profile and configuration data
                  </p>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <ArrowRight className="text-blue-400 rotate-90" size={28} />
              </div>

              {/* Step 3 */}
              <div className="flex items-start gap-4">
                <div className="bg-cyan-500 rounded-full w-12 h-12 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <span className="text-white font-bold text-xl">3</span>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="text-cyan-400" size={20} />
                    <h3 className="text-white font-semibold text-lg">Process Input Files</h3>
                  </div>
                  <p className="text-slate-300 mb-3">
                    Read and parse files with smart chunking (1000 chars per chunk)
                  </p>
                  <div className="grid grid-cols-4 gap-2">
                    <div className="bg-slate-800 rounded px-3 py-2 text-center text-cyan-300 text-sm">JSON</div>
                    <div className="bg-slate-800 rounded px-3 py-2 text-center text-cyan-300 text-sm">JSONL</div>
                    <div className="bg-slate-800 rounded px-3 py-2 text-center text-cyan-300 text-sm">CSV</div>
                    <div className="bg-slate-800 rounded px-3 py-2 text-center text-cyan-300 text-sm">TXT</div>
                  </div>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <ArrowRight className="text-blue-400 rotate-90" size={28} />
              </div>

              {/* Step 4 */}
              <div className="flex items-start gap-4">
                <div className="bg-purple-500 rounded-full w-12 h-12 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <span className="text-white font-bold text-xl">4</span>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Cloud className="text-purple-400" size={20} />
                    <h3 className="text-white font-semibold text-lg">AI Enhancement via Bedrock</h3>
                  </div>
                  <p className="text-slate-300">
                    Process documents through AWS Bedrock using Anthropic models for enrichment
                  </p>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <ArrowRight className="text-blue-400 rotate-90" size={28} />
              </div>

              {/* Step 5 */}
              <div className="flex items-start gap-4">
                <div className="bg-yellow-500 rounded-full w-12 h-12 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <span className="text-white font-bold text-xl">5</span>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Search className="text-yellow-400" size={20} />
                    <h3 className="text-white font-semibold text-lg">Index to Elasticsearch</h3>
                  </div>
                  <p className="text-slate-300">
                    Bulk index enriched documents (50 docs per batch) into Elasticsearch cluster
                  </p>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <ArrowRight className="text-blue-400 rotate-90" size={28} />
              </div>

              {/* Step 6 */}
              <div className="flex items-start gap-4">
                <div className="bg-green-500 rounded-full w-12 h-12 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <span className="text-white font-bold text-xl">6</span>
                </div>
                <div className="flex-1 bg-slate-700/50 rounded-xl p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="text-green-400" size={20} />
                    <h3 className="text-white font-semibold text-lg">Stream SSE Updates & Complete</h3>
                  </div>
                  <p className="text-slate-300">
                    Real-time progress updates sent via Server-Sent Events throughout the pipeline
                  </p>
                </div>
              </div>
            </div>

            {/* Configuration Note */}
            <div className="mt-12 pt-8 border-t border-slate-700">
              <div className="bg-blue-900/30 border border-blue-500/50 rounded-xl p-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="text-blue-400 flex-shrink-0 mt-1" size={24} />
                  <div>
                    <h3 className="text-blue-300 font-semibold mb-2">Pipeline Configuration</h3>
                    <ul className="text-slate-300 space-y-1 text-sm">
                      <li>• <span className="text-blue-400">Chunk Size:</span> 1000 characters per chunk</li>
                      <li>• <span className="text-blue-400">Batch Size:</span> 50 documents per Elasticsearch batch</li>
                      <li>• <span className="text-blue-400">Output:</span> Real-time JSON event stream via SSE</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GenerativeIndexingDiagrams;