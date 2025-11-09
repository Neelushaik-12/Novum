import React, { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API || 'http://localhost:5001/api'
//const adminAllowedDomains = (process.env.NEXT_PUBLIC_ADMIN_DOMAINS || 'ealliancecorp.com').split(',').map(d => d.trim().toLowerCase()).filter(Boolean)
const forbiddenAdminDomains = (process.env.NEXT_PUBLIC_FORBIDDEN_ADMIN_DOMAINS || 'gmail.com,outlook.com,yahoo.com,hotmail.com,live.com,icloud.com,protonmail.com').split(',').map(d => d.trim().toLowerCase()).filter(Boolean)

export default function Home() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('seeker')
  const [user, setUser] = useState(null)
  const [jobs, setJobs] = useState([])
  const [file, setFile] = useState(null)
  const [matches, setMatches] = useState([])
  const [showRegister, setShowRegister] = useState(false)
  const [editingJob, setEditingJob] = useState(null)

  useEffect(() => {
    try {
      if (typeof window === 'undefined') return
      const stored = localStorage.getItem('jobmatch_user')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (parsed && parsed.id) {
          setUser(parsed)
          if (parsed.role === 'seeker') {
            window.location.href = '/seeker'
          }
        }
      }
    } catch (err) {
      console.error('Failed to load stored user:', err)
    }
  }, [])

  const register = async () => {
    try {
      if (!username || !password || !name) {
        alert('Please fill in all required fields')
        return
      }

      if (role === 'admin') {
        const emailDomain = (username.split('@')[1] || '').toLowerCase()
        if (!emailDomain || forbiddenAdminDomains.includes(emailDomain)) {
          alert('Admin accounts must use a company domain (personal email providers are not allowed).')
          return
        }
      }

      const res = await fetch(`${API}/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password, name, role })})
      const data = await res.json()
      alert(data.ok ? 'Registered' : data.error)
    } catch (err) {
      console.error('Registration failed:', err)
      alert('Registration failed. Please try again.')
    }
  }

  const login = async () => {
    try {
      const res = await fetch(`${API}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      
      const data = await res.json();
      if (data.ok) {
        setUser(data.user);
        // Save user to localStorage for seeker page
        localStorage.setItem('jobmatch_user', JSON.stringify(data.user));
        // Redirect seekers to seeker page
        if (data.user.role === 'seeker') {
          window.location.href = '/seeker';
        }
      } else {
        alert(data.error || "Login failed");
      }
    } catch (err) {
      console.error("Login failed:", err);
      alert("Could not connect to backend. Check server and API URL.");
    }
  };  

  const listJobs = async () => {
    try {
      const res = await fetch(`${API}/jobs`)
      const data = await res.json()
      setJobs(data || [])
    } catch (err) {
      console.error('Failed to load jobs:', err)
      setJobs([])
    }
  }
  
  // Auto-load jobs when admin logs in
  useEffect(() => {
    if (user && user.role === 'admin') {
      listJobs()
    }
  }, [user])

  const createJob = async (title, description, skillsCsv, responsibilities, qualifications, companyName, hrEmail) => {
    if (!user) return alert('login first')
    if (!title || !description) return alert('Title and description are required')
    const skills = skillsCsv ? skillsCsv.split(',').map(s => s.trim()).filter(Boolean) : []
    try {
      const res = await fetch(`${API}/jobs`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ 
          title, 
          description, 
          skills, 
          responsibilities: responsibilities || [],
          qualifications: qualifications || [],
          company_name: companyName || '',
          hr_email: hrEmail || '',
          created_by: user.id 
        })
      })
      const data = await res.json()
      if (data.ok) {
        alert('Job created successfully!')
        listJobs()
        // Clear form
        return true
      } else {
        alert(data.error || 'Failed to create job')
        return false
      }
    } catch (err) {
      console.error('Create job error:', err)
      alert('Failed to create job. Check server connection.')
      return false
    }
  }

  const editJob = async (jobId, title, description, skillsCsv, responsibilities, qualifications, companyName, hrEmail) => {
    if (!user) return false
    const skills = skillsCsv ? skillsCsv.split(',').map(s => s.trim()).filter(Boolean) : []
    try {
      const res = await fetch(`${API}/jobs/${jobId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          title, 
          description, 
          skills, 
          responsibilities: responsibilities || [],
          qualifications: qualifications || [],
          company_name: companyName || '',
          hr_email: hrEmail || ''
        })
      })
      const data = await res.json()
      if (data.ok) {
        alert('Job updated successfully!')
        listJobs()
        return true
      } else {
        alert(data.error || 'Failed to update job')
        return false
      }
    } catch (err) {
      console.error('Update job error:', err)
      alert('Failed to update job. Check server connection.')
      return false
    }
  }

  const deleteJob = async (jobId) => {
    if (!user) return false
    try {
      const res = await fetch(`${API}/jobs/${jobId}`, { method: 'DELETE' })
      const data = await res.json()
      if (data.ok) {
        alert('Job deleted successfully!')
        listJobs()
        return true
      } else {
        alert(data.error || 'Failed to delete job')
        return false
      }
    } catch (err) {
      console.error('Delete job error:', err)
      alert('Failed to delete job. Check server connection.')
      return false
    }
  }

  const uploadResume = async () => {
    if (!user || !file) return
    const fd = new FormData(); fd.append('user_id', user.id); fd.append('file', file)
    const res = await fetch(`${API}/upload-resume`, { method: 'POST', body: fd })
    const data = await res.json(); if (!data.ok) alert(data.error)
  }
  const handleMatch = async () => {
    const res = await fetch("http://localhost:5000/api/rag-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_text: resumeText,
        top_k: 5,
        rerank_with_llm: true
      }),
    });
    const data = await res.json();
  
    if (data.ok) {
      setMatches(data.results); // 'results' instead of 'matches'
    } else {
      console.error(data.error);
    }
  };
  const runMatch = async () => {
    const res = await fetch(`${API}/match`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: user.id })})
    const data = await res.json(); if (data.ok) setMatches(data.matches)
  }

  const logout = () => {
    try {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('jobmatch_user')
      }
    } catch (err) {
      console.error('Failed to clear stored user:', err)
    }
    setUser(null)
    setMatches([])
    setFile(null)
    if (typeof window !== 'undefined') {
      window.location.href = '/'
    }
  }

  return (
    <div style={pageBg}>
      {user && user.role === 'admin' ? (
        <div style={nav}>
          <div style={navInner}>
            <a href='/' style={{ textDecoration: 'none', color: '#111827', fontWeight: 700 }}>JobMatch</a>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div>Admin Dashboard</div>
              <button
                onClick={logout}
                style={{ padding: '6px 12px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      ) : (
        <NavBar />
      )}
      <div style={{ width: '100%', maxWidth: 1120, margin: '0 auto', padding: user && user.role === 'admin' ? '24px 16px' : '32px 16px' }}>
        {!user && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 24, alignItems: 'center' }}>
            <Hero />
            {!showRegister ? <LoginCard {...{username,password,setUsername,setPassword,login,setShowRegister}} /> : <RegisterCard {...{name,username,password,role,setName,setUsername,setPassword,setRole,register,setShowRegister}} />}
          </div>
        )}

        {user && (
          <div>
            {user.role === 'admin' ? (
              <>
                {/* Admin Welcome Banner */}
                <div style={{ ...card, marginBottom: 24, background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: '#fff' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h2 style={{ margin: 0, marginBottom: 8, fontSize: 24, fontWeight: 700 }}>Welcome, {user.name || 'Admin'}!</h2>
                      <div style={{ fontSize: 14, opacity: 0.9 }}>{user.username}</div>
                      <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>Admin Dashboard - Job Management</div>
                    </div>
                    <div style={{ fontSize: 48 }}>👔</div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                  {/* Left side: Create Job Form */}
                  <div style={card}>
                    <h3 style={cardTitle}>Create New Job Posting</h3>
                    <JobForm onCreate={createJob} />
                  </div>
                  
                  {/* Right side: Jobs List */}
                  <div style={card}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                      <h3 style={{ margin: 0 }}>Created Jobs ({jobs.length})</h3>
                      <button style={{...outlineBtn, marginTop: 0, padding: '6px 12px', fontSize: 13}} onClick={listJobs}>Refresh</button>
                    </div>
                    <JobsList jobs={jobs} onEdit={setEditingJob} onDelete={deleteJob} onRefresh={listJobs} />
                  </div>
                  
                  {/* Edit Job Modal */}
                  {editingJob && (
                    <EditJobModal
                      job={editingJob}
                      onSave={editJob}
                      onCancel={() => setEditingJob(null)}
                    />
                  )}
                </div>
              </>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <div style={card}>
                  <h3 style={cardTitle}>Your Profile</h3>
                  <div style={{ color: '#4b5563' }}>Welcome {user.name} ({user.role})</div>
                </div>
              </div>
            )}

            {user.role === 'seeker' && (
              <div style={cardFull}>
                <h3 style={cardTitle}>Seeker — Resume & Matching</h3>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input type='file' onChange={e=>setFile(e.target.files?.[0]||null)} />
                  <button style={outlineBtn} onClick={uploadResume}>Upload Resume</button>
                  <button style={primaryBtn} onClick={runMatch}>Run Matching</button>
                </div>
                <div style={{ marginTop: 12 }}>
                  {matches.map(({ job, similarity }) => (
                    <div key={job.id} style={jobCard}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{job.title}</div>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>{(similarity*100).toFixed(2)}% match</div>
                        {job.company_name && (
                          <div style={{ fontSize: 12, color: '#6b7280' }}>🏢 {job.company_name}</div>
                        )}
                      </div>
                      <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                        {job.source === 'local' ? (
                          <>
                            <a
                              href={`/questions/${job.id}`}
                              style={{
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
                          </>
                        ) : (
                          job.apply_link ? (
                            <a
                              href={job.apply_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
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
                          ) : (
                            <span style={{ fontSize: 11, color: '#6b7280' }}>
                              External listing — apply via company site.
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      <Footer />
    </div>
  )
}

function EditJobModal({ job, onSave, onCancel }){
  const [title, setTitle] = useState(job.title || '')
  const [description, setDescription] = useState(job.description || '')
  const [skills, setSkills] = useState(Array.isArray(job.skills) ? job.skills.join(', ') : (job.skills || ''))
  const [responsibilities, setResponsibilities] = useState(Array.isArray(job.responsibilities) ? job.responsibilities.join('\n') : (job.responsibilities || ''))
  const [qualifications, setQualifications] = useState(Array.isArray(job.qualifications) ? job.qualifications.join('\n') : (job.qualifications || ''))
  const [companyName, setCompanyName] = useState(job.company_name || '')
  const [hrEmail, setHrEmail] = useState(job.hr_email || '')
  
  const handleSubmit = async () => {
    if (!title || !description) {
      alert('Title and description are required')
      return
    }
    const success = await onSave(job.id, title, description, skills, responsibilities, qualifications, companyName, hrEmail)
    if (success) {
      onCancel()
    }
  }
  
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        ...card,
        maxWidth: 600,
        maxHeight: '90vh',
        overflowY: 'auto',
        width: '90%'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={cardTitle}>Edit Job</h3>
          <button onClick={onCancel} style={{ background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', color: '#6b7280' }}>×</button>
        </div>
        <JobFormFields
          title={title} setTitle={setTitle}
          description={description} setDescription={setDescription}
          skills={skills} setSkills={setSkills}
          responsibilities={responsibilities} setResponsibilities={setResponsibilities}
          qualifications={qualifications} setQualifications={setQualifications}
          companyName={companyName} setCompanyName={setCompanyName}
          hrEmail={hrEmail} setHrEmail={setHrEmail}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button style={primaryBtn} onClick={handleSubmit}>Save Changes</button>
          <button style={outlineBtn} onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

function JobFormFields({ title, setTitle, description, setDescription, skills, setSkills, responsibilities, setResponsibilities, qualifications, setQualifications, companyName, setCompanyName, hrEmail, setHrEmail }){
  return (
    <div style={{ display: 'flex', gap: 12, flexDirection: 'column' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <label style={{ fontSize: 14, color: '#333', fontWeight: 500, marginBottom: 4, display: 'block' }}>Job Title *</label>
          <input 
            style={inputStyle} 
            placeholder='e.g., Software Engineer' 
            value={title} 
            onChange={e=>setTitle(e.target.value)} 
          />
        </div>
        
        <div>
          <label style={{ fontSize: 14, color: '#333', fontWeight: 500, marginBottom: 4, display: 'block' }}>Company Name</label>
          <input 
            style={inputStyle} 
            placeholder='e.g., Tech Corp Inc.' 
            value={companyName} 
            onChange={e=>setCompanyName(e.target.value)} 
          />
        </div>
      </div>
      
      <div>
        <label style={{ fontSize: 14, color: '#333', fontWeight: 500, marginBottom: 4, display: 'block' }}>HR Email</label>
        <input 
          type='email'
          style={inputStyle} 
          placeholder='hr@company.com' 
          value={hrEmail} 
          onChange={e=>setHrEmail(e.target.value)} 
        />
      </div>
      
      <div>
        <label style={{ fontSize: 14, color: '#333', fontWeight: 500, marginBottom: 4, display: 'block' }}>Description *</label>
        <textarea 
          style={{...inputStyle, minHeight: 100, resize: 'vertical'}} 
          placeholder='Job description and overview...' 
          value={description} 
          onChange={e=>setDescription(e.target.value)} 
        />
      </div>
      
      <div>
        <label style={{ fontSize: 14, color: '#333', fontWeight: 500, marginBottom: 4, display: 'block' }}>Skills (comma separated)</label>
        <input 
          style={inputStyle} 
          placeholder='e.g., Python, React, SQL' 
          value={skills} 
          onChange={e=>setSkills(e.target.value)} 
        />
      </div>
      
      <div>
        <label style={{ fontSize: 14, color: '#333', fontWeight: 500, marginBottom: 4, display: 'block' }}>Responsibilities (one per line)</label>
        <textarea 
          style={{...inputStyle, minHeight: 120, resize: 'vertical'}} 
          placeholder='• Develop and maintain software applications&#10;• Collaborate with cross-functional teams&#10;• Write clean and efficient code' 
          value={responsibilities} 
          onChange={e=>setResponsibilities(e.target.value)} 
        />
        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Enter each responsibility on a new line</div>
      </div>
      
      <div>
        <label style={{ fontSize: 14, color: '#333', fontWeight: 500, marginBottom: 4, display: 'block' }}>Qualifications (one per line)</label>
        <textarea 
          style={{...inputStyle, minHeight: 120, resize: 'vertical'}} 
          placeholder='• Bachelor&#39;s degree in Computer Science&#10;• 3+ years of experience&#10;• Strong problem-solving skills' 
          value={qualifications} 
          onChange={e=>setQualifications(e.target.value)} 
        />
        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Enter each qualification on a new line</div>
      </div>
    </div>
  )
}

function JobForm({ onCreate }){
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [skills, setSkills] = useState('')
  const [responsibilities, setResponsibilities] = useState('')
  const [qualifications, setQualifications] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [hrEmail, setHrEmail] = useState('')
  
  const handleSubmit = async () => {
    if (!title || !description) {
      alert('Title and description are required')
      return
    }
    const success = await onCreate(title, description, skills, responsibilities, qualifications, companyName, hrEmail)
    if (success) {
      // Clear form on success
      setTitle('')
      setDescription('')
      setSkills('')
      setResponsibilities('')
      setQualifications('')
      setCompanyName('')
      setHrEmail('')
    }
  }
  
  return (
    <div>
      <JobFormFields
        title={title} setTitle={setTitle}
        description={description} setDescription={setDescription}
        skills={skills} setSkills={setSkills}
        responsibilities={responsibilities} setResponsibilities={setResponsibilities}
        qualifications={qualifications} setQualifications={setQualifications}
        companyName={companyName} setCompanyName={setCompanyName}
        hrEmail={hrEmail} setHrEmail={setHrEmail}
      />
      <button style={primaryBtn} onClick={handleSubmit}>Create Job</button>
    </div>
  )
}

function JobsList({ jobs, onEdit, onDelete, onRefresh }){
  const [expandedJob, setExpandedJob] = useState(null)
  const [deletingJobId, setDeletingJobId] = useState(null)
  
  const handleDelete = async (jobId, e) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this job?')) return
    setDeletingJobId(jobId)
    try {
      await onDelete(jobId)
    } finally {
      setDeletingJobId(null)
    }
  }
  
  const handleEdit = (job, e) => {
    e.stopPropagation()
    onEdit(job)
  }
  
  const handleCreateLink = (job, e) => {
    e.stopPropagation()
    // Generate questions and open in new page
    window.location.href = `/questions/${job.id}`
  }
  
  if (!jobs || jobs.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>📋</div>
        <div style={{ fontSize: 14 }}>No jobs created yet</div>
        <div style={{ fontSize: 12, marginTop: 4, opacity: 0.7 }}>Create your first job using the form on the left</div>
      </div>
    )
  }
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: '70vh', overflowY: 'auto' }}>
      {jobs.map(job => (
        <div 
          key={job.id} 
          style={{
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            padding: 16,
            background: expandedJob === job.id ? '#f9fafb' : '#fff',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
          onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 16, color: '#111827', marginBottom: 4 }}>
                {job.title || 'Untitled Job'}
              </div>
              {(job.company_name || job.hr_email) && (
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>
                  {job.company_name && <span>🏢 {job.company_name}</span>}
                </div>
              )}
              <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>
                {job.description ? (job.description.length > 100 ? job.description.substring(0, 100) + '...' : job.description) : 'No description'}
              </div>
              
              {expandedJob === job.id && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #e5e7eb' }}>
                  {(job.company_name || job.hr_email) && (
                    <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: '1px solid #e5e7eb' }}>
                      {job.company_name && (
                        <div style={{ marginBottom: 8 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 4 }}>Company Name</div>
                          <div style={{ fontSize: 13, color: '#4b5563' }}>🏢 {job.company_name}</div>
                        </div>
                      )}
                      {job.hr_email && (
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 4 }}>HR Email</div>
                          <div style={{ fontSize: 13, color: '#4b5563' }}>
                            📧 <a href={`mailto:${job.hr_email}`} style={{ color: '#3b82f6', textDecoration: 'none' }}>{job.hr_email}</a>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Description</div>
                    <div style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.6 }}>{job.description || 'No description provided'}</div>
                  </div>
                  
                  {job.skills && job.skills.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Skills</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {job.skills.map((skill, idx) => (
                          <span key={idx} style={{ 
                            padding: '4px 10px', 
                            background: '#eef2ff', 
                            color: '#4338ca', 
                            borderRadius: 12, 
                            fontSize: 12 
                          }}>
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {job.responsibilities && job.responsibilities.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Responsibilities</div>
                      <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#4b5563', lineHeight: 1.8 }}>
                        {job.responsibilities.map((resp, idx) => (
                          <li key={idx}>{resp}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {job.qualifications && job.qualifications.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Qualifications</div>
                      <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#4b5563', lineHeight: 1.8 }}>
                        {job.qualifications.map((qual, idx) => (
                          <li key={idx}>{qual}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 12 }}>
                    Job ID: {job.id}
                  </div>
                  
                  {/* Action Buttons */}
                  <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #e5e7eb', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      onClick={(e) => handleEdit(job, e)}
                      style={{
                        padding: '6px 12px',
                        background: '#3b82f6',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: 500
                      }}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={(e) => handleDelete(job.id, e)}
                      disabled={deletingJobId === job.id}
                      style={{
                        padding: '6px 12px',
                        background: deletingJobId === job.id ? '#9ca3af' : '#ef4444',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        cursor: deletingJobId === job.id ? 'not-allowed' : 'pointer',
                        fontSize: 12,
                        fontWeight: 500,
                        opacity: deletingJobId === job.id ? 0.6 : 1
                      }}
                    >
                      {deletingJobId === job.id ? '⏳ Deleting...' : '🗑️ Delete'}
                    </button>
                    <button
                      onClick={(e) => handleCreateLink(job, e)}
                      style={{
                        padding: '6px 12px',
                        background: '#10b981',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: 500
                      }}
                    >
                      🔗 Create Link
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div style={{ marginLeft: 12, fontSize: 20, color: '#9ca3af' }}>
              {expandedJob === job.id ? '▼' : '▶'}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

const inputStyle = {
  padding: '10px 12px',
  border: '1px solid #d9d9e3',
  borderRadius: 8,
  outline: 'none'
}

const primaryBtn = {
  marginTop: 8,
  padding: '10px 12px',
  borderRadius: 8,
  background: '#3b82f6',
  color: '#fff',
  border: 'none',
  cursor: 'pointer'
}

const outlineBtn = {
  marginTop: 8,
  padding: '10px 12px',
  borderRadius: 8,
  background: '#fff',
  color: '#374151',
  border: '1px solid #d1d5db',
  cursor: 'pointer'
}

const pageBg = {
  minHeight: '100vh',
  background: 'linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)',
  fontFamily: 'Inter, system-ui, sans-serif'
}

const nav = {
  width: '100%',
  borderBottom: '1px solid #e5e7eb',
  background: 'rgba(255,255,255,0.6)',
  backdropFilter: 'saturate(180%) blur(8px)'
}
const navInner = { maxWidth: 1120, margin: '0 auto', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }

function NavBar(){
  return (
    <div style={nav}>
      <div style={navInner}>
        <div style={{ fontWeight: 700 }}>JobMatch</div>
        <div style={{ fontSize: 14, color: '#6b7280' }}>AI-powered job portal</div>
      </div>
    </div>
  )
}

function Hero(){
  return (
    <div>
      <div style={{ fontSize: 40, fontWeight: 800, lineHeight: 1.1 }}>Discover roles tailored to you</div>
      <div style={{ marginTop: 8, color: '#4b5563', maxWidth: 520 }}>Upload your resume and let our AI match you with the best opportunities. Apply faster with tailored screening questions.</div>
      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <span style={{ padding: '8px 12px', borderRadius: 999, background: '#eef2ff', color: '#4338ca', fontSize: 12 }}>Smart matching</span>
        <span style={{ padding: '8px 12px', borderRadius: 999, background: '#ecfeff', color: '#047857', fontSize: 12 }}>Fast apply</span>
      </div>
    </div>
  )
}

const card = { background: '#fff', border: '1px solid #e6e6ef', borderRadius: 12, padding: 20, boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }
const cardFull = { ...card, gridColumn: '1 / -1' }
const cardTitle = { marginTop: 0, marginBottom: 12 }
const jobCard = { border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, margin: '10px 0', background: '#fafafa' }

function LoginCard({ username, password, setUsername, setPassword, login, setShowRegister }){
  return (
    <div style={card}>
      <h3 style={cardTitle}>Sign in</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <label style={{ fontSize: 14, color: '#333' }}>Email</label>
        <input style={inputStyle} placeholder='you@example.com' value={username} onChange={e=>setUsername(e.target.value)} />
        <label style={{ fontSize: 14, color: '#333' }}>Password</label>
        <input style={inputStyle} placeholder='••••••••' type='password' value={password} onChange={e=>setPassword(e.target.value)} />
        <button style={primaryBtn} onClick={login}>Sign in</button>
      </div>
      <div style={{ marginTop: 12, fontSize: 14, color: '#555', textAlign: 'center' }}>
        New to JobMatch?{' '}
        <a href="#" onClick={(e)=>{e.preventDefault(); setShowRegister(true)}}>Create an account</a>
      </div>
    </div>
  )
}

function RegisterCard({ name, username, password, role, setName, setUsername, setPassword, setRole, register, setShowRegister }){
  return (
    <div style={card}>
      <h3 style={cardTitle}>Create your account</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <label style={{ fontSize: 14, color: '#333' }}>Full name</label>
        <input style={inputStyle} placeholder='Jane Doe' value={name} onChange={e=>setName(e.target.value)} />
        <label style={{ fontSize: 14, color: '#333' }}>Email</label>
        <input style={inputStyle} placeholder='you@example.com' value={username} onChange={e=>setUsername(e.target.value)} />
        <label style={{ fontSize: 14, color: '#333' }}>Password</label>
        <input style={inputStyle} placeholder='Create a password' type='password' value={password} onChange={e=>setPassword(e.target.value)} />
        <label style={{ fontSize: 14, color: '#333' }}>Role</label>
        <select style={inputStyle} value={role} onChange={e=>setRole(e.target.value)}>
          <option value='seeker'>Job Seeker</option>
          <option value='admin'>Admin (create jobs)</option>
        </select>
        <button style={primaryBtn} onClick={register}>Create account</button>
      </div>
      <div style={{ marginTop: 12, fontSize: 14, color: '#555', textAlign: 'center' }}>
        Already have an account?{' '}
        <a href="#" onClick={(e)=>{e.preventDefault(); setShowRegister(false)}}>Sign in</a>
      </div>
    </div>
  )
}

function Footer(){
  return (
    <div style={{ marginTop: 32, padding: '16px 0', textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
      © {new Date().getFullYear()} JobMatch. All rights reserved.
    </div>
  )
}


