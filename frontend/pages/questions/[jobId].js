import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'

const API = process.env.NEXT_PUBLIC_API || 'http://localhost:5001/api'

export default function QuestionsPage() {
  const router = useRouter()
  const { jobId } = router.query
  const [job, setJob] = useState(null)
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [experienceLevel, setExperienceLevel] = useState('mid-level')
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [user, setUser] = useState(null)

  const isAdmin = user?.role === 'admin'

  const logout = () => {
    try {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('jobmatch_user')
      }
    } catch (err) {
      console.error('Failed to clear stored user:', err)
    }
    setUser(null)
    router.push('/')
  }

  const normalizeQuestions = (items) => {
    if (!items) return []

    let list = items
    if (typeof list === 'string') {
      try {
        const parsed = JSON.parse(list)
        if (Array.isArray(parsed)) {
          list = parsed
        } else {
          list = []
        }
      } catch (err) {
        console.error('Failed to parse questions payload:', err)
        list = []
      }
    }

    if (!Array.isArray(list)) return []

    return list
      .map((item, idx) => {
        if (typeof item === 'string') {
          return { id: idx, question: item }
        }
        if (item && typeof item === 'object') {
          if (item.question) return { id: idx, question: item.question }
          if (item.text) return { id: idx, question: item.text }
        }
        return { id: idx, question: String(item ?? '') }
      })
      .filter(q => q.question && q.question.trim().length > 0)
  }

  useEffect(() => {
    try {
      const stored = typeof window !== 'undefined' ? localStorage.getItem('jobmatch_user') : null
      if (!stored) {
        router.push('/')
        return
      }
      const parsed = JSON.parse(stored)
      if (!parsed || !parsed.id) {
        router.push('/')
        return
      }
      setUser(parsed)
    } catch (err) {
      console.error('Failed to load user:', err)
      router.push('/')
    }
  }, [])

  useEffect(() => {
    if (jobId) {
      loadJob()
    }
  }, [jobId])

  const loadJob = async () => {
    try {
      const res = await fetch(`${API}/jobs/${jobId}`)
      const data = await res.json()
      if (data.error) {
        alert('Job not found')
        router.push('/')
        return
      }
      const jobData = data.job || data
      if (jobData) {
        setJob(jobData)
        const normalized = normalizeQuestions(jobData.questions)
        setQuestions(normalized)
        setAnswers({})
      } else {
        alert('Job not found')
        router.push('/')
      }
    } catch (err) {
      console.error('Failed to load job:', err)
      alert('Failed to load job')
      router.push('/')
    }
  }

  const generateQuestions = async () => {
    if (!jobId || !isAdmin) {
      alert('Only admins can generate questions.')
      return
    }
    setGenerating(true)
    setSaveMessage('')
    try {
      const res = await fetch(`${API}/jobs/${jobId}/generate-questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ experience_level: experienceLevel })
      })
      const data = await res.json()
      if (data.error) {
        alert(data.error || 'Failed to generate questions')
        return
      }
      const newQuestions = Array.isArray(data.questions) ? data.questions : data.questions?.questions
      if (newQuestions && Array.isArray(newQuestions)) {
        const normalized = normalizeQuestions(newQuestions)
        setQuestions(normalized)
        setAnswers({})
        alert('Questions generated successfully!')
      } else {
        alert('Failed to generate questions')
      }
    } catch (err) {
      console.error('Failed to generate questions:', err)
      alert('Failed to generate questions')
    } finally {
      setGenerating(false)
    }
  }

  const handleQuestionChange = (idx, value) => {
    setQuestions(prev => prev.map((q, index) => index === idx ? { ...q, question: value } : q))
  }

  const addQuestion = () => {
    setQuestions(prev => [...prev, { id: prev.length, question: '' }])
  }

  const removeQuestion = (idx) => {
    setQuestions(prev => prev.filter((_, index) => index !== idx))
  }

  const saveQuestions = async () => {
    if (!jobId || !isAdmin) return
    setSaving(true)
    setSaveMessage('')
    setError('')
    try {
      const payload = {
        questions: questions.map(q => (q?.question || '').trim()).filter(Boolean)
      }
      const res = await fetch(`${API}/jobs/${jobId}/save-questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()
      if (!res.ok || data.ok === false) {
        throw new Error(data.error || `Server error: ${res.status}`)
      }
      const normalized = normalizeQuestions(data.questions)
      setQuestions(normalized)
      setSaveMessage('Questions saved successfully.')
    } catch (err) {
      console.error('Failed to save questions:', err)
      setError(err.message || 'Failed to save questions.')
    } finally {
      setSaving(false)
    }
  }

  const handleSubmit = async () => {
    if (!user || !user.id) {
      alert('Please log in again to submit your answers.')
      router.push('/')
      return
    }
    if (questions.length === 0) {
      setError('No questions are available for this job yet. Please contact the hiring team.')
      return
    }

    const unanswered = questions.filter((_, idx) => {
      const key = String(idx + 1)
      return !answers[key] || !answers[key].trim()
    })
    if (unanswered.length > 0) {
      setError(`Please answer all questions. ${unanswered.length} question(s) remaining.`)
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const payload = {
        user_id: user.id,
        job,
        questions: questions.map(q => ({ question: q.question })),
        answers
      }
      const res = await fetch(`${API}/submit-answers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()
      if (!res.ok || data.ok === false) {
        throw new Error(data.error || `Server error: ${res.status}`)
      }
      setResult(data)
      setSubmitted(true)
    } catch (err) {
      console.error('Matching error:', err)
      setError(err.message || 'Failed to submit answers. Please try again later.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!job) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: '#6b7280' }}>Loading...</div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <div style={{ width: '100%', maxWidth: 900, margin: '0 auto', padding: '32px 16px' }}>
        {/* Header */}
        <div style={{ background: '#fff', border: '1px solid #e6e6ef', borderRadius: 12, padding: 24, marginBottom: 24, boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <h1 style={{ margin: 0, marginBottom: 8, fontSize: 28, fontWeight: 700, color: '#111827' }}>{job.title}</h1>
              {job.company_name && (
                <div style={{ fontSize: 16, color: '#6b7280', marginBottom: 4 }}>🏢 {job.company_name}</div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => {
                  if (typeof window !== 'undefined' && window.history.length > 1) {
                    router.back()
                  } else {
                    router.push(isAdmin ? '/' : '/seeker')
                  }
                }}
                style={{ padding: '8px 16px', background: '#f3f4f6', color: '#374151', borderRadius: 8, fontSize: 14, border: '1px solid #d1d5db', cursor: 'pointer' }}
              >
                ← Back
              </button>
              <button
                onClick={logout}
                style={{ padding: '8px 16px', background: '#ef4444', color: '#fff', borderRadius: 8, fontSize: 14, border: 'none', cursor: 'pointer' }}
              >
                Logout
              </button>
            </div>
          </div>
          
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 8 }}>Job Description</div>
            <div style={{ fontSize: 14, color: '#4b5563', lineHeight: 1.6 }}>{job.description}</div>
          </div>

          {job.skills && job.skills.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 8 }}>Required Skills</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {job.skills.map((skill, idx) => (
                  <span key={idx} style={{ padding: '4px 10px', background: '#eef2ff', color: '#4338ca', borderRadius: 12, fontSize: 12 }}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Questions Section */}
        <div style={{ background: '#fff', border: '1px solid #e6e6ef', borderRadius: 12, padding: 24, boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: '#111827' }}>Technical Questions</h2>
            {isAdmin && (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <select
                  value={experienceLevel}
                  onChange={(e) => setExperienceLevel(e.target.value)}
                  style={{ padding: '6px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }}
                >
                  <option value='entry'>Entry Level</option>
                  <option value='mid-level'>Mid Level</option>
                  <option value='senior'>Senior Level</option>
                </select>
                <button
                  onClick={generateQuestions}
                  disabled={generating}
                  style={{
                    padding: '8px 16px',
                    background: generating ? '#9ca3af' : '#3b82f6',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 6,
                    cursor: generating ? 'not-allowed' : 'pointer',
                    fontSize: 14,
                    fontWeight: 500
                  }}
                >
                  {generating ? '⏳ Generating...' : '🔗 Generate Questions'}
                </button>
              </div>
            )}
          </div>

          {saveMessage && (
            <div style={{
              marginBottom: 16,
              padding: '10px 14px',
              background: '#ecfdf5',
              border: '1px solid #10b981',
              borderRadius: 8,
              color: '#047857',
              fontSize: 13
            }}>
              {saveMessage}
            </div>
          )}

          {error && (
            <div style={{
              marginBottom: 16,
              padding: '10px 14px',
              background: '#fee2e2',
              border: '1px solid #fecaca',
              borderRadius: 8,
              color: '#991b1b',
              fontSize: 13
            }}>
              {error}
            </div>
          )}

          {questions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>❓</div>
              <div style={{ fontSize: 16, marginBottom: 8 }}>No questions prepared yet</div>
              {isAdmin ? (
                <div style={{ fontSize: 14 }}>Use the generator above to create questions for this job.</div>
              ) : (
                <div style={{ fontSize: 14 }}>The hiring team has not published assessment questions for this job yet. Please check back later.</div>
              )}
            </div>
          ) : (
            <div>
              {isAdmin ? (
                <>
                  {questions.map((questionObj, idx) => (
                    <div key={idx} style={{ marginBottom: 24, paddingBottom: 24, borderBottom: idx < questions.length - 1 ? '1px solid #e5e7eb' : 'none' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>Question {idx + 1}</div>
                        <button
                          onClick={() => removeQuestion(idx)}
                          style={{ fontSize: 12, color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}
                        >
                          Remove
                        </button>
                      </div>
                      <textarea
                        value={questionObj.question || ''}
                        onChange={(e) => handleQuestionChange(idx, e.target.value)}
                        placeholder='Enter question text...'
                        style={{
                          width: '100%',
                          minHeight: 80,
                          padding: '12px',
                          border: '1px solid #d1d5db',
                          borderRadius: 8,
                          fontSize: 14,
                          fontFamily: 'inherit',
                          resize: 'vertical',
                          outline: 'none'
                        }}
                      />
                    </div>
                  ))}
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={addQuestion}
                      style={{
                        padding: '10px 16px',
                        background: '#f3f4f6',
                        color: '#374151',
                        border: '1px solid #d1d5db',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: 13
                      }}
                    >
                      + Add Question
                    </button>
                    <button
                      onClick={saveQuestions}
                      disabled={saving}
                      style={{
                        padding: '10px 18px',
                        background: saving ? '#9ca3af' : '#10b981',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        cursor: saving ? 'not-allowed' : 'pointer',
                        fontSize: 14,
                        fontWeight: 600
                      }}
                    >
                      {saving ? 'Saving…' : 'Save Questions'}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {questions.map((questionObj, idx) => {
                    const answerKey = String(idx + 1)
                    return (
                      <div key={idx} style={{ marginBottom: 24, paddingBottom: 24, borderBottom: idx < questions.length - 1 ? '1px solid #e5e7eb' : 'none' }}>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                          Question {idx + 1}: {questionObj.question}
                        </div>
                        <textarea
                          value={answers[answerKey] || ''}
                          onChange={(e) => setAnswers({ ...answers, [answerKey]: e.target.value })}
                          placeholder='Type your answer here...'
                          disabled={submitted || submitting}
                          onPaste={(e) => {
                            e.preventDefault()
                            alert('Copy/paste is disabled. Please type your answer manually.')
                          }}
                          onCopy={(e) => {
                            e.preventDefault()
                          }}
                          onCut={(e) => {
                            e.preventDefault()
                          }}
                          onDrop={(e) => {
                            e.preventDefault()
                          }}
                          style={{
                            width: '100%',
                            minHeight: 120,
                            padding: '12px',
                            border: '1px solid #d1d5db',
                            borderRadius: 8,
                            fontSize: 14,
                            fontFamily: 'inherit',
                            resize: 'vertical',
                            outline: 'none'
                          }}
                        />
                        <div style={{ fontSize: 11, color: '#6b7280', marginTop: 6 }}>
                          Copy/Paste is disabled for security. Please type your answer.
                        </div>
                      </div>
                    )
                  })}
                  {!submitted && (
                    <button
                      onClick={handleSubmit}
                      disabled={submitting}
                      style={{
                        padding: '12px 24px',
                        background: submitting ? '#9ca3af' : '#10b981',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 8,
                        cursor: submitting ? 'not-allowed' : 'pointer',
                        fontSize: 16,
                        fontWeight: 600,
                        width: '100%'
                      }}
                    >
                      {submitting ? 'Submitting…' : 'Submit Answers'}
                    </button>
                  )}
                  {submitted && result && (
                    <div style={{
                      marginTop: 16,
                      padding: '16px',
                      background: result.status === 'passed' ? '#ecfdf5' : '#fef2f2',
                      border: `1px solid ${result.status === 'passed' ? '#10b981' : '#fca5a5'}`,
                      borderRadius: 8,
                      textAlign: 'left',
                      color: result.status === 'passed' ? '#047857' : '#991b1b',
                      fontSize: 14,
                      lineHeight: 1.6
                    }}>
                      <div><strong>Assessment Submitted!</strong></div>
                      <div>Score: <strong>{(result.score ?? 0).toFixed(2)}%</strong></div>
                      <div>Status: <strong>{(result.status || '').toUpperCase()}</strong></div>
                      {job.hr_email && (
                        <div>Results have been emailed to <strong>{job.hr_email}</strong>.</div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

