# Troubleshooting Job Search

## Common Issues and Solutions

### Issue: "Start Matching" button doesn't work / No jobs found

#### 1. Check if you have uploaded a resume
- The matching feature requires a resume to be uploaded
- Make sure you select a file and it uploads successfully before clicking "Start Matching"

#### 2. Check SERPAPI_KEY configuration
The job search requires a SerpAPI key to fetch jobs from company websites.

**To set it up:**
1. Sign up for a free account at https://serpapi.com/
2. Get your API key from the dashboard
3. Add it to your `.env` file:
   ```
   SERPAPI_KEY=your_actual_api_key_here
   ```
4. Restart your Flask server

**Check if it's configured:**
- Visit `http://localhost:5001/api/debug` to see configuration status
- Or check the browser console/network tab for error messages

#### 3. Test the API directly

**Check debug endpoint:**
```bash
curl http://localhost:5001/api/debug
```

**Test match endpoint (replace USER_ID with actual user ID):**
```bash
curl -X POST http://localhost:5001/api/match \
  -H "Content-Type: application/json" \
  -d '{"user_id": "YOUR_USER_ID"}'
```

#### 4. Check server logs
Look at your Flask server console for error messages. Common errors:
- `SERPAPI_KEY not set` - Add your API key to .env
- `No resume found` - Upload a resume first
- `SerpAPI request error` - Check your API key validity or internet connection

#### 5. Verify resume was saved
1. Check if resume exists in database
2. Visit debug endpoint to see resume count
3. Try uploading resume again

### Issue: Jobs found but not displayed

1. **Check browser console** for JavaScript errors
2. **Check network tab** in browser DevTools to see API response
3. **Verify matches array** - The response should have `{"ok": true, "matches": [...]}`

### Issue: External jobs not showing (only local jobs)

- This means SERPAPI_KEY is working but no external jobs were found
- Try adjusting your resume keywords
- Check if your query is too specific
- Verify SerpAPI has results by checking their dashboard

### Testing without SERPAPI_KEY

If you don't have a SerpAPI key, you can still test with local jobs:
1. Use the employer portal to create sample jobs
2. Or call `/api/generate-sample` to create test data
3. Then try matching

### Getting Help

If you're still having issues:
1. Check the Flask server console for detailed error logs
2. Check browser DevTools console and network tab
3. Use the `/api/debug` endpoint to verify configuration
4. Make sure all required environment variables are set in `.env`

