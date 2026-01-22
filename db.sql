-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.activity_log (
  id bigint NOT NULL DEFAULT nextval('activity_log_id_seq'::regclass),
  user_id bigint NOT NULL,
  username text,
  first_name text,
  activity_type text NOT NULL CHECK (activity_type = ANY (ARRAY['comment'::text, 'reaction'::text, 'referral'::text, 'joining'::text, 'boost'::text, 'quiz'::text])),
  points integer NOT NULL,
  timestamp timestamp with time zone NOT NULL DEFAULT now(),
  post_id bigint,
  post_timestamp timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  channel_id character varying,
  CONSTRAINT activity_log_pkey PRIMARY KEY (id)
);
CREATE TABLE public.activity_log_archive (
  id bigint NOT NULL DEFAULT nextval('activity_log_archive_id_seq'::regclass),
  user_id bigint NOT NULL,
  username text,
  first_name text,
  activity_type text NOT NULL,
  points integer NOT NULL,
  timestamp timestamp with time zone NOT NULL,
  post_id bigint,
  post_timestamp timestamp with time zone,
  archive_timestamp text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  channel_id character varying,
  CONSTRAINT activity_log_archive_pkey PRIMARY KEY (id)
);
CREATE TABLE public.daily_logs (
  id bigint NOT NULL DEFAULT nextval('daily_logs_id_seq'::regclass),
  user_id bigint,
  log_date date NOT NULL,
  symptoms ARRAY,
  mood character varying,
  pain_level integer CHECK (pain_level >= 0 AND pain_level <= 10),
  notes text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT daily_logs_pkey PRIMARY KEY (id),
  CONSTRAINT daily_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(telegram_id)
);
CREATE TABLE public.instagram_requests (
  id bigint NOT NULL DEFAULT nextval('instagram_requests_id_seq'::regclass),
  user_id bigint NOT NULL,
  username text,
  first_name text,
  last_name text,
  channel_id text NOT NULL,
  channel_name text NOT NULL,
  status text NOT NULL DEFAULT 'pending'::text,
  timestamp timestamp with time zone NOT NULL,
  processed_at timestamp with time zone,
  processed_by bigint,
  CONSTRAINT instagram_requests_pkey PRIMARY KEY (id)
);
CREATE TABLE public.periods (
  id bigint NOT NULL DEFAULT nextval('periods_id_seq'::regclass),
  user_id bigint,
  start_date date NOT NULL,
  end_date date,
  cycle_length integer DEFAULT 28,
  period_length integer DEFAULT 5,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT periods_pkey PRIMARY KEY (id),
  CONSTRAINT periods_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(telegram_id)
);
CREATE TABLE public.questions (
  id bigint NOT NULL DEFAULT nextval('questions_id_seq'::regclass),
  user_id bigint NOT NULL,
  username text,
  question text NOT NULL,
  status text NOT NULL DEFAULT 'pending'::text CHECK (status = ANY (ARRAY['pending'::text, 'answered'::text, 'archived'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  answered_at timestamp with time zone,
  answered_by bigint,
  CONSTRAINT questions_pkey PRIMARY KEY (id),
  CONSTRAINT fk_questions_user FOREIGN KEY (user_id) REFERENCES public.uzbek_europe_users(user_id)
);
CREATE TABLE public.referrals (
  id bigint NOT NULL DEFAULT nextval('referrals_id_seq'::regclass),
  referrer_id bigint NOT NULL,
  referred_user_id bigint NOT NULL UNIQUE,
  referred_username text,
  referred_first_name text,
  timestamp timestamp with time zone NOT NULL,
  referrer_username character varying,
  referrer_first_name character varying,
  CONSTRAINT referrals_pkey PRIMARY KEY (id)
);
CREATE TABLE public.reminders (
  id bigint NOT NULL DEFAULT nextval('reminders_id_seq'::regclass),
  user_id bigint,
  reminder_type character varying,
  reminder_date date NOT NULL,
  sent boolean DEFAULT false,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT reminders_pkey PRIMARY KEY (id),
  CONSTRAINT reminders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(telegram_id)
);
CREATE TABLE public.search_history (
  id bigint NOT NULL DEFAULT nextval('search_history_id_seq'::regclass),
  user_id bigint,
  query_text text NOT NULL,
  query_type character varying,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT search_history_pkey PRIMARY KEY (id),
  CONSTRAINT search_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users_simpletravel(telegram_id)
);
CREATE TABLE public.user_sessions (
  id bigint NOT NULL DEFAULT nextval('user_sessions_id_seq'::regclass),
  telegram_id bigint,
  session_key character varying NOT NULL,
  session_value text,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone,
  CONSTRAINT user_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT user_sessions_telegram_id_fkey FOREIGN KEY (telegram_id) REFERENCES public.users_simpletravel(telegram_id)
);
CREATE TABLE public.user_settings (
  id bigint NOT NULL DEFAULT nextval('user_settings_id_seq'::regclass),
  user_id bigint UNIQUE,
  cycle_length integer DEFAULT 28,
  period_length integer DEFAULT 5,
  notification_enabled boolean DEFAULT true,
  notification_days_before integer DEFAULT 2,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT user_settings_pkey PRIMARY KEY (id),
  CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(telegram_id)
);
CREATE TABLE public.users (
  id bigint NOT NULL DEFAULT nextval('users_id_seq'::regclass),
  telegram_id bigint NOT NULL UNIQUE,
  username character varying,
  first_name character varying,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.users_simpletravel (
  id bigint NOT NULL DEFAULT nextval('users_simpletravel_id_seq'::regclass),
  telegram_id bigint NOT NULL UNIQUE,
  username character varying,
  first_name character varying,
  last_name character varying,
  language_code character varying DEFAULT 'en'::character varying,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT users_simpletravel_pkey PRIMARY KEY (id)
);
CREATE TABLE public.uzbek_europe_users (
  id bigint NOT NULL DEFAULT nextval('uzbek_europe_users_id_seq'::regclass),
  user_id bigint NOT NULL UNIQUE,
  username text,
  first_name text,
  last_name text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT uzbek_europe_users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.work_users (
  id bigint NOT NULL DEFAULT nextval('work_users_id_seq'::regclass),
  user_id bigint NOT NULL UNIQUE,
  first_name text,
  last_name text,
  username text,
  started_at timestamp with time zone NOT NULL DEFAULT now(),
  last_interaction timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT work_users_pkey PRIMARY KEY (id)
);