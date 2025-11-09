import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'

const API = process.env.NEXT_PUBLIC_API || 'http://localhost:5001/api'
const MATCHES_STORAGE_KEY = 'jobmatch_seeker_matches'
const PROFILE_STORAGE_PREFIX = 'jobmatch_seeker_profile_'

export default function Seeker() {
  const router = useRouter()
  const [user, setUser] = useState(null)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [yearsExp, setYearsExp] = useState('')
  const [skills, setSkills] = useState('')
  const [coverLetter, setCoverLetter] = useState('')
  const [file, setFile] = useState(null)
  const [resumeUploaded, setResumeUploaded] = useState(false) // Track if resume is uploaded
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [resumeError, setResumeError] = useState('') // Error message for resume upload
  const [preferredLocation, setPreferredLocation] = useState('')
  const [jobType, setJobType] = useState('any') // remote / onsite / hybrid / any

  useEffect(() => {
    try {
      const stored = typeof window !== 'undefined' ? localStorage.getItem('jobmatch_user') : null
      if (!stored) {
        router.push('/')
      } else {
        const parsed = JSON.parse(stored)
        if (!parsed || parsed.role !== 'seeker') {
          router.push('/')
        } else {
          setUser(parsed)
          const storedMatches = typeof window !== 'undefined' ? sessionStorage.getItem(MATCHES_STORAGE_KEY) : null
          if (storedMatches) {
            try {
              const parsedMatches = JSON.parse(storedMatches)
              if (Array.isArray(parsedMatches)) {
                const normalizedMatches = parsedMatches.map(match => {
                  if (!match || !match.job) return match
                  const job = { ...match.job }

                  if (typeof job.questions === 'string') {
                    try {
                      const parsedQuestions = JSON.parse(job.questions)
                      if (Array.isArray(parsedQuestions)) {
                        job.questions = parsedQuestions
                      }
                    } catch (err) {
                      console.error('Failed to parse stored job.questions:', err)
                      job.questions = []
                    }
                  }

                  if (!Array.isArray(job.questions)) {
                    job.questions = []
                  }

                  return { ...match, job }
                })
                setMatches(normalizedMatches)
              }
            } catch (err) {
              console.error('Failed to restore matches:', err)
            }
          }
        }
      }
    } catch {
      router.push('/')
    }
  }, [])

  useEffect(() => {
    if (!user) return
    try {
      const storedProfile = typeof window !== 'undefined' ? localStorage.getItem(PROFILE_STORAGE_PREFIX + user.id) : null
      if (storedProfile) {
        const parsed = JSON.parse(storedProfile)
        if (parsed && typeof parsed === 'object') {
          setFullName(parsed.fullName ?? user.name ?? '')
          setEmail(parsed.email ?? user.username ?? '')
          setPhone(parsed.phone ?? '')
          setYearsExp(parsed.yearsExp ?? '')
          setSkills(parsed.skills ?? '')
          setCoverLetter(parsed.coverLetter ?? '')
          setPreferredLocation(parsed.preferredLocation ?? '')
          setJobType(parsed.jobType ?? 'any')
        }
      } else {
        setFullName(user.name || '')
        setEmail(user.username || '')
      }
    } catch (err) {
      console.error('Failed to restore profile:', err)
      setFullName(user.name || '')
      setEmail(user.username || '')
    }
  }, [user])

  useEffect(() => {
    if (!user) return
    try {
      if (typeof window !== 'undefined') {
        const profile = {
          fullName,
          email,
          phone,
          yearsExp,
          skills,
          coverLetter,
          preferredLocation,
          jobType
        }
        localStorage.setItem(PROFILE_STORAGE_PREFIX + user.id, JSON.stringify(profile))
      }
    } catch (err) {
      console.error('Failed to persist profile:', err)
    }
  }, [user, fullName, email, phone, yearsExp, skills, coverLetter, preferredLocation, jobType])

  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        if (matches && matches.length > 0) {
          sessionStorage.setItem(MATCHES_STORAGE_KEY, JSON.stringify(matches))
        } else {
          sessionStorage.removeItem(MATCHES_STORAGE_KEY)
        }
      }
    } catch (err) {
      console.error('Failed to persist matches:', err)
    }
  }, [matches])

  const checkResumeExists = async (userId) => {
    try {
      // Check if user has a resume by trying to get it
      // We'll use a simple check - if the user has uploaded before, 
      // the resume will be available when they try to match
      // For now, we'll assume no resume exists and let the user upload
      // This prevents unnecessary API calls on page load
      setResumeUploaded(false)
    } catch (err) {
      // Silently fail - user will need to upload resume
      console.log('No previous resume found')
      setResumeUploaded(false)
    }
  }

  const uploadResume = async () => {
    if (!user || !file) {
      setResumeError('Please select a resume file to upload')
      return false
    }
    try {
      setResumeError('')
      const fd = new FormData()
      fd.append('user_id', user.id)
      fd.append('file', file)
      const res = await fetch(`${API}/upload-resume`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!data.ok) {
        throw new Error(data.error || 'Failed to upload resume')
      }
      setResumeUploaded(true)
      setResumeError('')
      return true
    } catch (err) {
      console.error('Upload error:', err)
      setResumeError('Failed to upload resume: ' + err.message)
      setResumeUploaded(false)
      throw new Error('Failed to upload resume: ' + err.message)
    }
  }

  const startMatching = async () => {
    setLoading(true)
    setError('')
    setResumeError('')
    setMatches([])
    
    try {
      if (!user) throw new Error('Please log in first')

      // VALIDATION: Check if resume is uploaded
      if (!file && !resumeUploaded) {
        setResumeError('Please upload your resume before starting matching')
        setLoading(false)
        return
      }

      // Upload resume if file is selected but not yet uploaded
      if (file && !resumeUploaded) {
        try {
          await uploadResume()
        } catch (uploadErr) {
          setResumeError(uploadErr.message)
          setLoading(false)
          return
        }
      }

      // Use RAG endpoint for better matching with explanations
      const res = await fetch(`${API}/rag-search`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ 
          user_id: user.id,
          top_k: 10,
          rerank_with_llm: true
        }) 
      })
      
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `Server error: ${res.status}`)
      if (data.ok === false) throw new Error(data.error || 'Failed to match jobs')

      // RAG endpoint returns results in 'results' or 'matches' field
      const matchesData = data.results || data.matches || []
      console.log('📊 Received RAG matches from backend:', matchesData.length, matchesData)
      
      // Filter by location and job type on frontend
      const filteredMatches = matchesData.filter(({job, similarity}) => {
        const locMatch = !preferredLocation || (job.location && job.location.toLowerCase().includes(preferredLocation.toLowerCase()))
        const typeMatch = jobType === 'any' || (job.job_type && job.job_type.toLowerCase() === jobType.toLowerCase()) || (job.title && job.title.toLowerCase().includes(jobType.toLowerCase())) || (job.description && job.description.toLowerCase().includes(jobType.toLowerCase()))
        return locMatch && typeMatch
      })
      
      setMatches(filteredMatches)

      if (!filteredMatches || filteredMatches.length === 0) {
        const errorMsg = data.message || 'No matching jobs found. Try uploading a more detailed resume or adjusting your search criteria.'
        setError(errorMsg)
      } else {
        setError('') // Clear error if matches found
        console.log(`✅ Successfully loaded ${filteredMatches.length} job matches using RAG`)
      }

    } catch (err) {
      console.error('Matching error:', err)
      setError(err.message || 'Failed to search for jobs. Please try again.')
      setMatches([])
    } finally {
      setLoading(false)
    }
  }

  // Separate local (admin-created) and external jobs
  // Note: matches are already filtered in startMatching function
  const localMatches = matches.filter(({job}) => job.source === 'local')
  const externalMatches = matches.filter(({job}) => job.source === 'external' || !job.source)

  const logout = () => {
    try {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('jobmatch_user')
        sessionStorage.removeItem(MATCHES_STORAGE_KEY)
      }
    } catch (err) {
      console.error('Failed to clear stored user:', err)
    }
    setUser(null)
    router.push('/')
  }

  const handleBackClick = () => {
    try {
      if (typeof window !== 'undefined' && window.history.length > 1) {
        router.back()
      } else {
        router.push('/')
      }
    } catch (err) {
      router.push('/')
    }
  }

  if (!user) {
    return (
      <div style={pageBg}>
        <div style={nav}><div style={navInner}><a href='/' style={{ textDecoration: 'none', color: '#111827', fontWeight: 700 }}>JobMatch</a><div>Seeker Profile</div></div></div>
        <div style={{ width: '100%', maxWidth: 1120, margin: '0 auto', padding: '24px 16px', textAlign: 'center' }}>
          <div style={{ color: '#6b7280', marginTop: 40 }}>Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div style={pageBg}>
      <div style={nav}><div style={navInner}>
        <a href='/' style={{ textDecoration: 'none', color: '#111827', fontWeight: 700 }}>JobMatch</a>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div>Seeker Profile</div>
          <button
            onClick={logout}
            style={{ padding: '6px 12px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
          >
            Logout
          </button>
        </div>
      </div></div>
      <div style={{ width: '100%', maxWidth: 1120, margin: '0 auto', padding: '24px 16px' }}>
        {/* User Info Banner */}
        <div style={{ ...card, marginBottom: 24, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ margin: 0, marginBottom: 8, fontSize: 24, fontWeight: 700 }}>Welcome, {user.name || 'User'}!</h2>
              <div style={{ fontSize: 14, opacity: 0.9 }}>{user.username || email}</div>
              <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>Job Seeker Profile</div>
            </div>
            <div style={{ fontSize: 48 }}>👤</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          <div style={card}>
            <h3 style={cardTitle}>Your Details</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Field label='Full name'><input style={input} value={fullName} onChange={e=>setFullName(e.target.value)} /></Field>
              <Field label='Email'><input style={input} value={email} onChange={e=>setEmail(e.target.value)} /></Field>
              <Field label='Phone'><input style={input} value={phone} onChange={e=>setPhone(e.target.value)} /></Field>
              <Field label='Years of experience'><input style={input} value={yearsExp} onChange={e=>setYearsExp(e.target.value)} /></Field>
              <Field label='Data skills (comma separated)' full>
                <input style={input} placeholder='python, sql, pandas, tableau' value={skills} onChange={e=>setSkills(e.target.value)} />
              </Field>
              <Field label='Cover letter' full>
                <textarea style={{ ...input, minHeight: 120 }} placeholder='Briefly explain your background and interests' value={coverLetter} onChange={e=>setCoverLetter(e.target.value)} />
              </Field>
              <Field label='Preferred location'><input style={input} value={preferredLocation} onChange={e=>setPreferredLocation(e.target.value)} /></Field>
              <Field label='Job type'>
                <select style={input} value={jobType} onChange={e=>setJobType(e.target.value)}>
                  <option value="any">Any</option>
                  <option value="remote">Remote</option>
                  <option value="onsite">Onsite</option>
                  <option value="hybrid">Hybrid</option>
                </select>
              </Field>
              <Field label='Upload resume' full>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <input 
                    type='file' 
                    accept='.pdf,.doc,.docx,.txt'
                    onChange={e=>{
                      const selectedFile = e.target.files?.[0] || null
                      setFile(selectedFile)
                      setResumeUploaded(false) // Reset uploaded status when new file is selected
                      setResumeError('') // Clear any previous errors
                      if (selectedFile) {
                        console.log('File selected:', selectedFile.name)
                      }
                    }}
                    style={{ display: 'none' }}
                    id='resume-upload-input'
                  />
                  <button
                    type='button'
                    onClick={() => {
                      document.getElementById('resume-upload-input').click()
                    }}
                    style={{ 
                      padding: '12px 16px', 
                      background: '#f3f4f6', 
                      border: '2px dashed #d1d5db', 
                      borderRadius: 8, 
                      cursor: 'pointer',
                      textAlign: 'center',
                      fontSize: 14,
                      color: '#374151',
                      fontWeight: 500,
                      transition: 'all 0.2s',
                      width: '100%'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = '#e5e7eb'
                      e.currentTarget.style.borderColor = '#9ca3af'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = '#f3f4f6'
                      e.currentTarget.style.borderColor = '#d1d5db'
                    }}
                  >
                    {file ? `📄 ${file.name}` : '📁 Choose File (PDF, DOC, DOCX, TXT)'}
                  </button>
                  {file && (
                    <button 
                      type='button'
                      onClick={(e) => {
                        e.stopPropagation()
                        setFile(null)
                        setResumeUploaded(false)
                        setResumeError('')
                        const input = document.getElementById('resume-upload-input')
                        if (input) input.value = ''
                      }}
                      style={{ 
                        padding: '6px 12px', 
                        background: '#ef4444', 
                        color: '#fff', 
                        border: 'none', 
                        borderRadius: 6, 
                        cursor: 'pointer',
                        fontSize: 12,
                        alignSelf: 'flex-start',
                        fontWeight: 500
                      }}
                    >
                      Remove File
                    </button>
                  )}
                  {resumeError && (
                    <div style={{ 
                      padding: '8px 12px', 
                      background: '#fee2e2', 
                      border: '1px solid #fecaca', 
                      borderRadius: 6, 
                      color: '#991b1b',
                      fontSize: 13,
                      marginTop: 8
                    }}>
                      {resumeError}
                    </div>
                  )}
                  {resumeUploaded && !resumeError && (
                    <div style={{ 
                      padding: '8px 12px', 
                      background: '#d1fae5', 
                      border: '1px solid #a7f3d0', 
                      borderRadius: 6, 
                      color: '#065f46',
                      fontSize: 13,
                      marginTop: 8
                    }}>
                      ✓ Resume uploaded successfully
                    </div>
                  )}
                </div>
              </Field>
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <button style={primaryBtn} onClick={startMatching} disabled={loading}>{loading ? 'Matching…' : 'Start Matching'}</button>
              <button style={{ ...primaryBtn, background: '#6b7280' }} onClick={handleBackClick}>Back</button>
            </div>
          </div>

          <div style={card}>
            <h3 style={cardTitle}>Matching Openings</h3>
            {error && (
              <div style={{ padding: '12px', background: '#fee2e2', border: '1px solid #fecaca', borderRadius: 8, marginBottom: 16, color: '#991b1b' }}>
                {error}
              </div>
            )}
            {!matches.length && !error && !loading && <div style={{ color: '#6b7280' }}>No matches yet. Upload a resume and click Start Matching.</div>}
            
            {/* Local Jobs (Admin-created) - Displayed First */}
            {localMatches.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <h4 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#111827' }}>Admin-Created Jobs</h4>
                  <span style={{ padding: '2px 8px', background: '#10b981', color: '#fff', borderRadius: 12, fontSize: 11, fontWeight: 500 }}>
                    {localMatches.length}
                  </span>
                </div>
                <div>
                  {localMatches.map(({ job, similarity }) => (
                    <JobCard key={job.id} job={job} similarity={similarity} />
                  ))}
                </div>
              </div>
            )}
            
            {/* External Jobs - Displayed Second */}
            {externalMatches.length > 0 && (
              <div>
                {localMatches.length > 0 && (
                  <div style={{ height: 1, background: '#e5e7eb', marginBottom: 16 }} />
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <h4 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#111827' }}>External Job Openings</h4>
                  <span style={{ padding: '2px 8px', background: '#3b82f6', color: '#fff', borderRadius: 12, fontSize: 11, fontWeight: 500 }}>
                    {externalMatches.length}
                  </span>
                </div>
                <div>
                  {externalMatches.map(({ job, similarity }) => (
                    <JobCard key={job.id} job={job} similarity={similarity} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function JobCard({ job, similarity }) {
  const [expanded, setExpanded] = useState(false)

  const hasQuestions = Array.isArray(job?.questions) && job.questions.length > 0
  const hasSkills = Array.isArray(job?.skills) && job.skills.length > 0
  const hasResponsibilities = Array.isArray(job?.responsibilities) && job.responsibilities.length > 0
  const hasQualifications = Array.isArray(job?.qualifications) && job.qualifications.length > 0

  return (
    <div style={jobCard}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>{job.title}</div>
          {job.company && (
            <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 2 }}>
              {job.company} {job.location && `• ${job.location}`} {job.job_type && `• ${job.job_type}`}
            </div>
          )}
          <div style={{ fontSize: 12, color: '#3b82f6', marginTop: 4, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span>{(similarity*100).toFixed(1)}% match</span>
            {job.source === 'external' && (
              <span style={{ padding: '2px 6px', background: '#dbeafe', borderRadius: 4, fontSize: 11 }}>
                External Job
              </span>
            )}
            {job.company_name && (
              <span style={{ fontSize: 12, color: '#6b7280' }}>
                {job.company_name}
              </span>
            )}
          </div>
        </div>
        {job.apply_link && (
          <a href={job.apply_link} target="_blank" rel="noopener noreferrer" 
             style={{ padding: '6px 12px', background: '#3b82f6', color: '#fff', textDecoration: 'none', borderRadius: 6, fontSize: 12 }}>
            Apply
          </a>
        )}
      </div>
      
      <div style={{ fontSize: 14, color: '#374151', lineHeight: 1.5 }}>
        {job.description ? (
          <>
            {expanded ? job.description : job.description.slice(0, 300) + (job.description.length > 300 ? '…' : '')}
            {job.description.length > 300 && (
              <span style={{color:'#3b82f6', cursor:'pointer', marginLeft:6}} onClick={()=>setExpanded(!expanded)}>
                {expanded ? 'Show less' : 'Read more'}
              </span>
            )}
            {expanded && (
              <>
                {hasSkills && (
                  <div style={{ marginTop: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Required Skills</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {job.skills.map((skill, idx) => (
                        <span key={idx} style={{ padding: '4px 10px', background: '#eef2ff', color: '#4338ca', borderRadius: 12, fontSize: 12 }}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {hasResponsibilities && (
                  <div style={{ marginTop: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Responsibilities</div>
                    <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#4b5563', lineHeight: 1.8 }}>
                      {job.responsibilities.map((resp, idx) => (
                        <li key={idx}>{resp}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {hasQualifications && (
                  <div style={{ marginTop: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Qualifications</div>
                    <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#4b5563', lineHeight: 1.8 }}>
                      {job.qualifications.map((qual, idx) => (
                        <li key={idx}>{qual}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </>
        ) : 'No description available'}
      </div>

      {job.source === 'local' && (
        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <a
            href={`/questions/${job.id}`}
            style={{
              alignSelf: 'flex-start',
              padding: '8px 14px',
              background: '#3b82f6',
              color: '#fff',
              borderRadius: 6,
              textDecoration: 'none',
              fontSize: 12,
              fontWeight: 600
            }}
          >
            Take Assessment
          </a>
          {job.hr_email && (
            <span style={{ fontSize: 11, color: '#6b7280' }}>
              Results will be sent to {job.hr_email}
            </span>
          )}
          {hasQuestions && (
            <span style={{ fontSize: 11, color: '#6b7280' }}>
              Assessment questions are available for this role.
            </span>
          )}
        </div>
      )}

      {job.source !== 'local' && job.apply_link && (
        <div style={{ marginTop: 16 }}>
          <a
            href={job.apply_link}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-block',
              padding: '8px 14px',
              background: '#10b981',
              color: '#fff',
              borderRadius: 6,
              textDecoration: 'none',
              fontSize: 12,
              fontWeight: 600
            }}
          >
            Apply Externally
          </a>
        </div>
      )}
    </div>
  )
}

function Field({ label, children, full }){
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, gridColumn: full ? '1 / -1' : undefined }}>
      <label style={{ fontSize: 13, color: '#374151' }}>{label}</label>
      {children}
    </div>
  )
}

const pageBg = { minHeight: '100vh', background: 'linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)', fontFamily: 'Inter, system-ui, sans-serif' }
const nav = { width: '100%', borderBottom: '1px solid #e5e7eb', background: 'rgba(255,255,255,0.6)', backdropFilter: 'saturate(180%) blur(8px)' }
const navInner = { maxWidth: 1120, margin: '0 auto', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }
const card = { background: '#fff', border: '1px solid #e6e6ef', borderRadius: 12, padding: 20, boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }
const cardTitle = { marginTop: 0, marginBottom: 12 }
const input = { padding: '10px 12px', border: '1px solid #d9d9e3', borderRadius: 8, outline: 'none' }
const primaryBtn = { padding: '10px 12px', borderRadius: 8, background: '#3b82f6', color: '#fff', border: 'none', cursor: 'pointer' }
const jobCard = { border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, margin: '10px 0', background: '#fafafa' }
