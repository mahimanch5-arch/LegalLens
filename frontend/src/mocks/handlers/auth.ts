import { http, HttpResponse, delay } from 'msw';
import type { User } from '@/api/types';
import { db, save } from '../db';

export const DEMO_USER: User = { id: 'usr_dana', name: 'Dana Whitfield', email: 'dana@whitfieldlaw.com', initials: 'DW' };

const unauthorized = () => HttpResponse.json({ code: 'unknown', message: 'Not signed in.' }, { status: 401 });

export const authHandlers = [
  http.post('/api/auth/login', async ({ request }) => {
    await delay(600);
    const { email, password } = (await request.json()) as { email?: string; password?: string };
    if (!email || !password || password.length < 4 || password === 'wrong') {
      return HttpResponse.json(
        { code: 'unknown', message: 'That email and password combination is incorrect.' },
        { status: 401 },
      );
    }
    db.state.signedIn = true;
    save();
    return HttpResponse.json({ ...DEMO_USER, email });
  }),

  http.post('/api/auth/logout', async () => {
    db.state.signedIn = false;
    save();
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/auth/me', async () => {
    await delay(150);
    return db.state.signedIn ? HttpResponse.json(DEMO_USER) : unauthorized();
  }),
];

export function requireAuth() {
  return db.state.signedIn ? null : unauthorized();
}
