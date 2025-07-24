# UI Frontend Service

This service provides the user interface for the IM2 platform using Next.js.

## Features

- Next.js 14 app router architecture
- TypeScript for type safety
- TailwindCSS for styling
- JWT Authentication flow
- Real-time job monitoring
- File upload with drag-and-drop
- Job management interface
- System status dashboard
- Responsive design
- Accessibility compliance (WCAG 2.1 AA)
- Internationalization (i18n) ready
- Notifications system

## Key Components

### Pages and Routes
- `/` - Dashboard
- `/login` - Authentication
- `/upload` - File upload interface
- `/jobs` - Job monitoring and history
- `/files` - File browser
- `/system` - System status and control
- `/profile` - User profile and settings

### Components
- `Dropzone` - File upload with drag-and-drop
- `JobList` - Job monitoring with real-time updates
- `JobDetails` - Detailed job information
- `FileUpload` - File upload with progress
- `SystemStatus` - Service health dashboard
- `NotificationCenter` - System notifications
- `AuthForms` - Login and registration

## Development

1. Install dependencies:
   ```
   npm install
   ```

2. Run development server:
   ```
   npm run dev
   ```

3. Build for production:
   ```
   npm run build
   ```

4. Start production server:
   ```
   npm start
   ```

## Environment Variables

Create a `.env.local` file with the following variables:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Docker Usage

Build the container:
```
docker build -t im2-ui-frontend .
```

Run the container:
```
docker run -p 3000:3000 im2-ui-frontend
```

## Configuration

The UI connects to the API Backend service for all data operations. Configure the connection in `.env` or through Docker environment variables.
