--
-- PostgreSQL database dump
--

\restrict H4bPxpZSU3Qo6aZ2SnEJvcDaeY5LCFv2t5Ld5ci1L06WzWc7pUsIQzlKR7egmcz

-- Dumped from database version 16.10
-- Dumped by pg_dump version 16.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: sync_space_tenant_id(); Type: FUNCTION; Schema: public; Owner: parking_user
--

CREATE FUNCTION public.sync_space_tenant_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Sync tenant_id from site
    IF NEW.site_id IS NOT NULL THEN
        NEW.tenant_id := (SELECT tenant_id FROM sites WHERE id = NEW.site_id);
    ELSIF NEW.site_id IS NULL THEN
        NEW.tenant_id := NULL;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.sync_space_tenant_id() OWNER TO parking_user;

--
-- Name: update_updated_at(); Type: FUNCTION; Schema: public; Owner: parking_user
--

CREATE FUNCTION public.update_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at() OWNER TO parking_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.api_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    key_hash character varying(255) NOT NULL,
    key_name character varying(100),
    last_used_at timestamp with time zone,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    tenant_id uuid
);


ALTER TABLE public.api_keys OWNER TO parking_user;

--
-- Name: device_assignments; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.device_assignments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    device_type character varying(50) NOT NULL,
    device_id uuid NOT NULL,
    dev_eui character varying(16) NOT NULL,
    space_id uuid,
    assigned_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    unassigned_at timestamp without time zone,
    assigned_by uuid,
    unassigned_by uuid,
    assignment_reason text,
    unassignment_reason text
);


ALTER TABLE public.device_assignments OWNER TO parking_user;

--
-- Name: display_devices; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.display_devices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    dev_eui character varying(16) NOT NULL,
    name character varying(255),
    status character varying(50) DEFAULT 'unassigned'::character varying NOT NULL,
    lifecycle_state character varying(50) DEFAULT 'provisioned'::character varying NOT NULL,
    assigned_space_id uuid,
    assigned_at timestamp without time zone,
    last_seen_at timestamp without time zone,
    enabled boolean DEFAULT true,
    config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.display_devices OWNER TO parking_user;

--
-- Name: gateways; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.gateways (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    gateway_id character varying(16) NOT NULL,
    name character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'offline'::character varying,
    site_id uuid,
    enabled boolean DEFAULT true,
    config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.gateways OWNER TO parking_user;

--
-- Name: orphan_devices; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.orphan_devices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dev_eui character varying(16) NOT NULL,
    first_seen timestamp without time zone NOT NULL,
    last_seen timestamp without time zone NOT NULL,
    message_count integer DEFAULT 1,
    last_payload text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.orphan_devices OWNER TO parking_user;

--
-- Name: reservations; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.reservations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    space_id uuid NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    user_email character varying(255),
    user_phone character varying(20),
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    tenant_id uuid,
    user_id uuid,
    user_name character varying(255),
    checked_in boolean DEFAULT false,
    checked_in_at timestamp without time zone,
    checked_out_at timestamp without time zone,
    rate double precision,
    total_cost double precision,
    payment_status character varying(50) DEFAULT 'pending'::character varying,
    cancelled_at timestamp without time zone,
    cancelled_by uuid,
    cancellation_reason text,
    notes text,
    CONSTRAINT valid_duration CHECK (((end_time - start_time) <= '24:00:00'::interval)),
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'cancelled'::character varying, 'no_show'::character varying])::text[]))),
    CONSTRAINT valid_times CHECK ((end_time > start_time))
);


ALTER TABLE public.reservations OWNER TO parking_user;

--
-- Name: sensor_devices; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.sensor_devices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    dev_eui character varying(16) NOT NULL,
    name character varying(255),
    status character varying(50) DEFAULT 'unassigned'::character varying NOT NULL,
    lifecycle_state character varying(50) DEFAULT 'provisioned'::character varying NOT NULL,
    assigned_space_id uuid,
    assigned_at timestamp without time zone,
    last_seen_at timestamp without time zone,
    enabled boolean DEFAULT true,
    config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.sensor_devices OWNER TO parking_user;

--
-- Name: sensor_readings; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.sensor_readings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    device_id uuid NOT NULL,
    dev_eui character varying(16) NOT NULL,
    fcnt integer NOT NULL,
    occupied boolean,
    rssi double precision,
    snr double precision,
    raw_payload text,
    received_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.sensor_readings OWNER TO parking_user;

--
-- Name: sites; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.sites (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    timezone character varying(50) DEFAULT 'UTC'::character varying,
    location jsonb,
    metadata jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.sites OWNER TO parking_user;

--
-- Name: TABLE sites; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON TABLE public.sites IS 'Physical locations within a tenant (multi-site support)';


--
-- Name: spaces; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.spaces (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(20) NOT NULL,
    building character varying(100),
    floor character varying(20),
    zone character varying(50),
    gps_latitude numeric(10,8),
    gps_longitude numeric(11,8),
    sensor_eui character varying(16),
    display_eui character varying(16),
    state character varying(20) DEFAULT 'FREE'::character varying NOT NULL,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    deleted_at timestamp with time zone,
    site_id uuid,
    tenant_id uuid,
    sensor_device_id uuid,
    display_device_id uuid,
    current_state character varying(50) DEFAULT 'unknown'::character varying,
    sensor_state character varying(50),
    display_state character varying(50),
    state_changed_at timestamp without time zone,
    enabled boolean DEFAULT true,
    auto_release_minutes integer,
    config jsonb DEFAULT '{}'::jsonb,
    display_name character varying(255),
    CONSTRAINT valid_gps CHECK ((((gps_latitude IS NULL) AND (gps_longitude IS NULL)) OR (((gps_latitude >= ('-90'::integer)::numeric) AND (gps_latitude <= (90)::numeric)) AND ((gps_longitude >= ('-180'::integer)::numeric) AND (gps_longitude <= (180)::numeric))))),
    CONSTRAINT valid_state CHECK (((state)::text = ANY ((ARRAY['FREE'::character varying, 'OCCUPIED'::character varying, 'RESERVED'::character varying, 'MAINTENANCE'::character varying])::text[])))
);


ALTER TABLE public.spaces OWNER TO parking_user;

--
-- Name: COLUMN spaces.tenant_id; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON COLUMN public.spaces.tenant_id IS 'Denormalized tenant_id for fast lookups without joins';


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.tenants (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    settings jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    type character varying(50) DEFAULT 'customer'::character varying,
    subscription_tier character varying(50) DEFAULT 'basic'::character varying,
    CONSTRAINT valid_slug CHECK (((slug)::text ~ '^[a-z0-9-]+$'::text))
);


ALTER TABLE public.tenants OWNER TO parking_user;

--
-- Name: TABLE tenants; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON TABLE public.tenants IS 'Organizations/tenants with strict data isolation';


--
-- Name: site_details; Type: VIEW; Schema: public; Owner: parking_user
--

CREATE VIEW public.site_details AS
 SELECT s.id AS site_id,
    s.name AS site_name,
    s.timezone,
    s.location,
    s.is_active AS site_active,
    t.id AS tenant_id,
    t.name AS tenant_name,
    t.slug AS tenant_slug,
    count(DISTINCT sp.id) AS space_count,
    count(DISTINCT sp.id) FILTER (WHERE ((sp.state)::text = 'FREE'::text)) AS free_spaces,
    count(DISTINCT sp.id) FILTER (WHERE ((sp.state)::text = 'OCCUPIED'::text)) AS occupied_spaces
   FROM ((public.sites s
     JOIN public.tenants t ON ((s.tenant_id = t.id)))
     LEFT JOIN public.spaces sp ON (((s.id = sp.site_id) AND (sp.deleted_at IS NULL))))
  WHERE ((s.is_active = true) AND (t.is_active = true))
  GROUP BY s.id, s.name, s.timezone, s.location, s.is_active, t.id, t.name, t.slug;


ALTER VIEW public.site_details OWNER TO parking_user;

--
-- Name: VIEW site_details; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON VIEW public.site_details IS 'Site information with occupancy statistics';


--
-- Name: state_changes; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.state_changes (
    id bigint NOT NULL,
    space_id uuid NOT NULL,
    previous_state character varying(20),
    new_state character varying(20) NOT NULL,
    source character varying(50) NOT NULL,
    request_id character varying(50),
    metadata jsonb,
    "timestamp" timestamp with time zone DEFAULT now()
);


ALTER TABLE public.state_changes OWNER TO parking_user;

--
-- Name: state_changes_id_seq; Type: SEQUENCE; Schema: public; Owner: parking_user
--

CREATE SEQUENCE public.state_changes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.state_changes_id_seq OWNER TO parking_user;

--
-- Name: state_changes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: parking_user
--

ALTER SEQUENCE public.state_changes_id_seq OWNED BY public.state_changes.id;


--
-- Name: user_memberships; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.user_memberships (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT valid_role CHECK (((role)::text = ANY ((ARRAY['owner'::character varying, 'admin'::character varying, 'operator'::character varying, 'viewer'::character varying])::text[])))
);


ALTER TABLE public.user_memberships OWNER TO parking_user;

--
-- Name: TABLE user_memberships; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON TABLE public.user_memberships IS 'Links users to tenants with role-based permissions';


--
-- Name: COLUMN user_memberships.role; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON COLUMN public.user_memberships.role IS 'owner: full access + billing; admin: manage site/users; operator: reservations/telemetry; viewer: read-only';


--
-- Name: tenant_summary; Type: VIEW; Schema: public; Owner: parking_user
--

CREATE VIEW public.tenant_summary AS
 SELECT t.id,
    t.name,
    t.slug,
    t.is_active,
    t.created_at,
    count(DISTINCT s.id) AS site_count,
    count(DISTINCT um.user_id) AS user_count,
    count(DISTINCT ak.id) AS api_key_count,
    count(DISTINCT sp.id) AS space_count
   FROM ((((public.tenants t
     LEFT JOIN public.sites s ON (((t.id = s.tenant_id) AND (s.is_active = true))))
     LEFT JOIN public.user_memberships um ON (((t.id = um.tenant_id) AND (um.is_active = true))))
     LEFT JOIN public.api_keys ak ON (((t.id = ak.tenant_id) AND (ak.is_active = true))))
     LEFT JOIN public.spaces sp ON (((t.id = sp.tenant_id) AND (sp.deleted_at IS NULL))))
  WHERE (t.is_active = true)
  GROUP BY t.id, t.name, t.slug, t.is_active, t.created_at;


ALTER VIEW public.tenant_summary OWNER TO parking_user;

--
-- Name: VIEW tenant_summary; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON VIEW public.tenant_summary IS 'Summary statistics for each active tenant';


--
-- Name: users; Type: TABLE; Schema: public; Owner: parking_user
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    email_verified boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_login_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO parking_user;

--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON TABLE public.users IS 'User accounts for authentication';


--
-- Name: user_permissions; Type: VIEW; Schema: public; Owner: parking_user
--

CREATE VIEW public.user_permissions AS
 SELECT u.id AS user_id,
    u.email,
    u.name,
    t.id AS tenant_id,
    t.name AS tenant_name,
    t.slug AS tenant_slug,
    um.role,
    um.is_active AS membership_active,
    u.is_active AS user_active
   FROM ((public.users u
     JOIN public.user_memberships um ON ((u.id = um.user_id)))
     JOIN public.tenants t ON ((um.tenant_id = t.id)))
  WHERE (u.is_active = true)
  ORDER BY u.email, t.name;


ALTER VIEW public.user_permissions OWNER TO parking_user;

--
-- Name: VIEW user_permissions; Type: COMMENT; Schema: public; Owner: parking_user
--

COMMENT ON VIEW public.user_permissions IS 'User access matrix across all tenants';


--
-- Name: state_changes id; Type: DEFAULT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.state_changes ALTER COLUMN id SET DEFAULT nextval('public.state_changes_id_seq'::regclass);


--
-- Data for Name: api_keys; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.api_keys (id, key_hash, key_name, last_used_at, is_active, created_at, tenant_id) FROM stdin;
67c1768f-1245-4c68-a573-558344c793f6	$2b$12$YourHashHere	Development Key	\N	t	2025-10-23 09:09:44.204243+00	00000000-0000-0000-0000-000000000001
\.


--
-- Data for Name: device_assignments; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.device_assignments (id, tenant_id, device_type, device_id, dev_eui, space_id, assigned_at, unassigned_at, assigned_by, unassigned_by, assignment_reason, unassignment_reason) FROM stdin;
\.


--
-- Data for Name: display_devices; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.display_devices (id, tenant_id, dev_eui, name, status, lifecycle_state, assigned_space_id, assigned_at, last_seen_at, enabled, config, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: gateways; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.gateways (id, tenant_id, gateway_id, name, status, site_id, enabled, config, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: orphan_devices; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.orphan_devices (id, dev_eui, first_seen, last_seen, message_count, last_payload, created_at) FROM stdin;
\.


--
-- Data for Name: reservations; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.reservations (id, space_id, start_time, end_time, user_email, user_phone, status, metadata, created_at, updated_at, tenant_id, user_id, user_name, checked_in, checked_in_at, checked_out_at, rate, total_cost, payment_status, cancelled_at, cancelled_by, cancellation_reason, notes) FROM stdin;
\.


--
-- Data for Name: sensor_devices; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.sensor_devices (id, tenant_id, dev_eui, name, status, lifecycle_state, assigned_space_id, assigned_at, last_seen_at, enabled, config, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sensor_readings; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.sensor_readings (id, tenant_id, device_id, dev_eui, fcnt, occupied, rssi, snr, raw_payload, received_at, created_at) FROM stdin;
\.


--
-- Data for Name: sites; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.sites (id, tenant_id, name, timezone, location, metadata, is_active, created_at, updated_at) FROM stdin;
00000000-0000-0000-0000-000000000001	00000000-0000-0000-0000-000000000001	Default Site	UTC	{"city": "Default", "country": "Unknown"}	{}	t	2025-10-23 09:10:13.515023+00	2025-10-23 09:10:13.515023+00
93250d86-2c81-4593-b9bb-769bc7332a0c	400edd20-47e9-43c0-b4e9-5dbb490f52aa	Main Parking Lot	UTC	{"address": "123 Main Street"}	{}	t	2025-10-23 09:26:18.90925+00	2025-10-23 09:26:18.90925+00
85a0b581-0a31-497e-876d-d494beb07a00	af92fb7e-8c56-4944-a456-8abf130cbff8	Main Site	UTC	{"address": "Demo Location"}	{}	t	2025-10-23 10:06:24.2863+00	2025-10-23 10:06:24.2863+00
\.


--
-- Data for Name: spaces; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.spaces (id, name, code, building, floor, zone, gps_latitude, gps_longitude, sensor_eui, display_eui, state, metadata, created_at, updated_at, deleted_at, site_id, tenant_id, sensor_device_id, display_device_id, current_state, sensor_state, display_state, state_changed_at, enabled, auto_release_minutes, config, display_name) FROM stdin;
39a2944a-0158-47e1-8968-2d04da8bbe95	Parking A-001	A001	Building A	Ground	North	\N	\N	\N	\N	FREE	\N	2025-10-23 09:09:44.206483+00	2025-10-23 09:10:13.51827+00	\N	00000000-0000-0000-0000-000000000001	00000000-0000-0000-0000-000000000001	\N	\N	unknown	\N	\N	\N	t	\N	{}	\N
ca78c4d3-e28e-42d1-a295-aff6f2f021c4	Parking A-002	A002	Building A	Ground	North	\N	\N	\N	\N	FREE	\N	2025-10-23 09:09:44.206483+00	2025-10-23 09:10:13.51827+00	\N	00000000-0000-0000-0000-000000000001	00000000-0000-0000-0000-000000000001	\N	\N	unknown	\N	\N	\N	t	\N	{}	\N
3e884c45-578c-4e54-85a8-e2fd27c26f35	Parking B-001	B001	Building B	Ground	South	\N	\N	\N	\N	FREE	\N	2025-10-23 09:09:44.206483+00	2025-10-23 09:10:13.51827+00	\N	00000000-0000-0000-0000-000000000001	00000000-0000-0000-0000-000000000001	\N	\N	unknown	\N	\N	\N	t	\N	{}	\N
5e3c1a83-1201-48e2-8adf-9546aa9713a9	Space A1	A1	\N	\N	\N	\N	\N	\N	\N	FREE	\N	2025-10-23 09:31:40.194097+00	2025-10-23 09:31:40.194097+00	\N	93250d86-2c81-4593-b9bb-769bc7332a0c	400edd20-47e9-43c0-b4e9-5dbb490f52aa	\N	\N	unknown	\N	\N	\N	t	\N	{}	Space A1
6dda88bc-b17b-43b3-98d0-5a65ba3a3d2a	Space B5	B5	\N	\N	\N	\N	\N	\N	\N	FREE	\N	2025-10-23 09:43:29.378965+00	2025-10-23 09:43:29.378965+00	\N	93250d86-2c81-4593-b9bb-769bc7332a0c	400edd20-47e9-43c0-b4e9-5dbb490f52aa	\N	\N	unknown	\N	\N	\N	t	\N	{}	Space B5
2bd03fc7-6fee-48f0-9fc8-86780b11d87b	Space C10	C10	\N	\N	\N	\N	\N	\N	\N	FREE	\N	2025-10-23 09:43:46.312301+00	2025-10-23 09:43:46.312301+00	\N	93250d86-2c81-4593-b9bb-769bc7332a0c	400edd20-47e9-43c0-b4e9-5dbb490f52aa	\N	\N	unknown	\N	\N	\N	t	\N	{}	Space C10
d9b634b9-86fa-49d9-86c8-3c0904895c3b	Space E20	E20	\N	\N	\N	\N	\N	\N	\N	FREE	\N	2025-10-23 09:45:45.292777+00	2025-10-23 09:45:45.292777+00	\N	93250d86-2c81-4593-b9bb-769bc7332a0c	400edd20-47e9-43c0-b4e9-5dbb490f52aa	\N	\N	unknown	\N	\N	\N	t	\N	{}	Space E20
3c7a0a1f-12f9-44e8-b763-e85d7d287a4d	Test Space TEST-1761214002	TEST-1761214002	\N	\N	\N	\N	\N	\N	\N	FREE	\N	2025-10-23 10:06:42.848657+00	2025-10-23 10:06:42.848657+00	\N	85a0b581-0a31-497e-876d-d494beb07a00	af92fb7e-8c56-4944-a456-8abf130cbff8	\N	\N	unknown	\N	\N	\N	t	\N	{}	Test Space TEST-1761214002
d9b0c17f-6161-45c1-baef-19009852ac99	Test Space TEST-1761214225	TEST-1761214225	\N	\N	\N	\N	\N	\N	\N	FREE	\N	2025-10-23 10:10:25.834045+00	2025-10-23 10:10:25.834045+00	\N	85a0b581-0a31-497e-876d-d494beb07a00	af92fb7e-8c56-4944-a456-8abf130cbff8	\N	\N	unknown	\N	\N	\N	t	\N	{}	Test Space TEST-1761214225
\.


--
-- Data for Name: state_changes; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.state_changes (id, space_id, previous_state, new_state, source, request_id, metadata, "timestamp") FROM stdin;
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.tenants (id, name, slug, metadata, settings, is_active, created_at, updated_at, type, subscription_tier) FROM stdin;
00000000-0000-0000-0000-000000000001	Default Organization	default	{"description": "Default tenant for backward compatibility"}	{}	t	2025-10-23 09:10:13.513602+00	2025-10-23 09:10:13.513602+00	customer	basic
00000000-0000-0000-0000-000000000000	Platform	platform	{}	{}	t	2025-10-23 09:11:40.995221+00	2025-10-23 09:11:40.995221+00	platform	enterprise
11e69704-b681-402d-95de-c467913c115b	Test Company	test-company	{}	{}	t	2025-10-23 09:18:40.753439+00	2025-10-23 09:18:40.753439+00	customer	basic
819aa601-5847-4e7b-9b32-f9c0c5c9224e	Test Company 2	test-company-2	{}	{}	t	2025-10-23 09:19:00.984412+00	2025-10-23 09:19:00.984412+00	customer	basic
7723ee83-0eb4-441a-ab9b-0ba1a687fffb	ACME Parking	acme-parking	{}	{}	t	2025-10-23 09:21:17.131191+00	2025-10-23 09:21:17.131191+00	customer	basic
400edd20-47e9-43c0-b4e9-5dbb490f52aa	City Parking Solutions	city-parking	{}	{}	t	2025-10-23 09:23:49.922982+00	2025-10-23 09:23:49.922982+00	customer	basic
af92fb7e-8c56-4944-a456-8abf130cbff8	Demo Parking Co	demo-parking	{}	{}	t	2025-10-23 10:02:06.432834+00	2025-10-23 10:02:06.432834+00	customer	basic
\.


--
-- Data for Name: user_memberships; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.user_memberships (id, user_id, tenant_id, role, metadata, is_active, created_at, updated_at) FROM stdin;
1ca1fac9-6d9c-41c9-8514-b83578d1fe3a	0431ad71-db44-4e6d-a982-65a1b4572bc5	400edd20-47e9-43c0-b4e9-5dbb490f52aa	owner	{}	t	2025-10-23 09:23:50.363784+00	2025-10-23 09:23:50.363784+00
0afd3143-599f-42f4-a0e6-c279ce7ceeb6	4798fde5-1a03-418f-be06-6cff57de5527	af92fb7e-8c56-4944-a456-8abf130cbff8	owner	{}	t	2025-10-23 10:02:06.862017+00	2025-10-23 10:02:06.862017+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: parking_user
--

COPY public.users (id, email, name, password_hash, metadata, is_active, email_verified, created_at, updated_at, last_login_at) FROM stdin;
0431ad71-db44-4e6d-a982-65a1b4572bc5	manager@cityparking.com	manager	$2b$12$y/vbIx5DOwAyxyBm7kByLOG0nBlkaqg.1u8jlxF.KdGcghgyfuxXi	{}	t	f	2025-10-23 09:23:50.360117+00	2025-10-23 09:23:50.360117+00	\N
4798fde5-1a03-418f-be06-6cff57de5527	demo@parkingco.com	demo_user	$2b$12$.z5Meo3tetHO0QshEXmTZuzeR9zCShmS/NsEog37wOLkBLQT4f1HK	{}	t	f	2025-10-23 10:02:06.858169+00	2025-10-23 10:02:06.858169+00	\N
\.


--
-- Name: state_changes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: parking_user
--

SELECT pg_catalog.setval('public.state_changes_id_seq', 1, false);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: device_assignments device_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_pkey PRIMARY KEY (id);


--
-- Name: display_devices display_devices_dev_eui_key; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.display_devices
    ADD CONSTRAINT display_devices_dev_eui_key UNIQUE (dev_eui);


--
-- Name: display_devices display_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.display_devices
    ADD CONSTRAINT display_devices_pkey PRIMARY KEY (id);


--
-- Name: gateways gateways_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.gateways
    ADD CONSTRAINT gateways_pkey PRIMARY KEY (id);


--
-- Name: orphan_devices orphan_devices_dev_eui_key; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.orphan_devices
    ADD CONSTRAINT orphan_devices_dev_eui_key UNIQUE (dev_eui);


--
-- Name: orphan_devices orphan_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.orphan_devices
    ADD CONSTRAINT orphan_devices_pkey PRIMARY KEY (id);


--
-- Name: reservations reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_pkey PRIMARY KEY (id);


--
-- Name: sensor_devices sensor_devices_dev_eui_key; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sensor_devices
    ADD CONSTRAINT sensor_devices_dev_eui_key UNIQUE (dev_eui);


--
-- Name: sensor_devices sensor_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sensor_devices
    ADD CONSTRAINT sensor_devices_pkey PRIMARY KEY (id);


--
-- Name: sensor_readings sensor_readings_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sensor_readings
    ADD CONSTRAINT sensor_readings_pkey PRIMARY KEY (id);


--
-- Name: sites sites_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sites
    ADD CONSTRAINT sites_pkey PRIMARY KEY (id);


--
-- Name: spaces spaces_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.spaces
    ADD CONSTRAINT spaces_pkey PRIMARY KEY (id);


--
-- Name: state_changes state_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.state_changes
    ADD CONSTRAINT state_changes_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_slug_key; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_slug_key UNIQUE (slug);


--
-- Name: api_keys unique_key_hash; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT unique_key_hash UNIQUE (key_hash);


--
-- Name: spaces unique_sensor_eui; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.spaces
    ADD CONSTRAINT unique_sensor_eui UNIQUE (sensor_eui);


--
-- Name: sites unique_tenant_site_name; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sites
    ADD CONSTRAINT unique_tenant_site_name UNIQUE (tenant_id, name);


--
-- Name: user_memberships unique_user_tenant; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.user_memberships
    ADD CONSTRAINT unique_user_tenant UNIQUE (user_id, tenant_id);


--
-- Name: user_memberships user_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.user_memberships
    ADD CONSTRAINT user_memberships_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_api_keys_active; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_api_keys_active ON public.api_keys USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_api_keys_tenant; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_api_keys_tenant ON public.api_keys USING btree (tenant_id) WHERE (is_active = true);


--
-- Name: idx_reservations_space; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_reservations_space ON public.reservations USING btree (space_id);


--
-- Name: idx_reservations_status; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_reservations_status ON public.reservations USING btree (status) WHERE ((status)::text = 'active'::text);


--
-- Name: idx_reservations_time; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_reservations_time ON public.reservations USING btree (start_time, end_time) WHERE ((status)::text = 'active'::text);


--
-- Name: idx_sensor_readings_device; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_sensor_readings_device ON public.sensor_readings USING btree (device_id);


--
-- Name: idx_sensor_readings_received; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_sensor_readings_received ON public.sensor_readings USING btree (received_at DESC);


--
-- Name: idx_sites_tenant; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_sites_tenant ON public.sites USING btree (tenant_id) WHERE (is_active = true);


--
-- Name: idx_sites_tenant_active; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_sites_tenant_active ON public.sites USING btree (tenant_id, is_active);


--
-- Name: idx_spaces_building; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_spaces_building ON public.spaces USING btree (building) WHERE (deleted_at IS NULL);


--
-- Name: idx_spaces_location; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_spaces_location ON public.spaces USING btree (building, floor, zone) WHERE (deleted_at IS NULL);


--
-- Name: idx_spaces_sensor; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_spaces_sensor ON public.spaces USING btree (sensor_eui) WHERE (deleted_at IS NULL);


--
-- Name: idx_spaces_site; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_spaces_site ON public.spaces USING btree (site_id) WHERE (deleted_at IS NULL);


--
-- Name: idx_spaces_state; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_spaces_state ON public.spaces USING btree (state) WHERE (deleted_at IS NULL);


--
-- Name: idx_spaces_tenant; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_spaces_tenant ON public.spaces USING btree (tenant_id) WHERE (deleted_at IS NULL);


--
-- Name: idx_state_changes_space; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_state_changes_space ON public.state_changes USING btree (space_id, "timestamp" DESC);


--
-- Name: idx_state_changes_timestamp_brin; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_state_changes_timestamp_brin ON public.state_changes USING brin ("timestamp");


--
-- Name: idx_tenants_active; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_tenants_active ON public.tenants USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_tenants_slug; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_tenants_slug ON public.tenants USING btree (slug) WHERE (is_active = true);


--
-- Name: idx_user_memberships_role; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_user_memberships_role ON public.user_memberships USING btree (tenant_id, role) WHERE (is_active = true);


--
-- Name: idx_user_memberships_tenant; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_user_memberships_tenant ON public.user_memberships USING btree (tenant_id) WHERE (is_active = true);


--
-- Name: idx_user_memberships_user; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_user_memberships_user ON public.user_memberships USING btree (user_id) WHERE (is_active = true);


--
-- Name: idx_users_active; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_users_active ON public.users USING btree (is_active);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE INDEX idx_users_email ON public.users USING btree (email) WHERE (is_active = true);


--
-- Name: unique_tenant_site_space_code; Type: INDEX; Schema: public; Owner: parking_user
--

CREATE UNIQUE INDEX unique_tenant_site_space_code ON public.spaces USING btree (tenant_id, site_id, code) WHERE (deleted_at IS NULL);


--
-- Name: spaces spaces_sync_tenant_id; Type: TRIGGER; Schema: public; Owner: parking_user
--

CREATE TRIGGER spaces_sync_tenant_id BEFORE INSERT OR UPDATE OF site_id ON public.spaces FOR EACH ROW EXECUTE FUNCTION public.sync_space_tenant_id();


--
-- Name: reservations update_reservations_updated_at; Type: TRIGGER; Schema: public; Owner: parking_user
--

CREATE TRIGGER update_reservations_updated_at BEFORE UPDATE ON public.reservations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


--
-- Name: sites update_sites_updated_at; Type: TRIGGER; Schema: public; Owner: parking_user
--

CREATE TRIGGER update_sites_updated_at BEFORE UPDATE ON public.sites FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


--
-- Name: spaces update_spaces_updated_at; Type: TRIGGER; Schema: public; Owner: parking_user
--

CREATE TRIGGER update_spaces_updated_at BEFORE UPDATE ON public.spaces FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


--
-- Name: tenants update_tenants_updated_at; Type: TRIGGER; Schema: public; Owner: parking_user
--

CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON public.tenants FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


--
-- Name: user_memberships update_user_memberships_updated_at; Type: TRIGGER; Schema: public; Owner: parking_user
--

CREATE TRIGGER update_user_memberships_updated_at BEFORE UPDATE ON public.user_memberships FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: parking_user
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


--
-- Name: device_assignments device_assignments_assigned_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(id);


--
-- Name: device_assignments device_assignments_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id);


--
-- Name: device_assignments device_assignments_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: device_assignments device_assignments_unassigned_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_unassigned_by_fkey FOREIGN KEY (unassigned_by) REFERENCES public.users(id);


--
-- Name: display_devices display_devices_assigned_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.display_devices
    ADD CONSTRAINT display_devices_assigned_space_id_fkey FOREIGN KEY (assigned_space_id) REFERENCES public.spaces(id) ON DELETE SET NULL;


--
-- Name: display_devices display_devices_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.display_devices
    ADD CONSTRAINT display_devices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: spaces fk_site; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.spaces
    ADD CONSTRAINT fk_site FOREIGN KEY (site_id) REFERENCES public.sites(id) ON DELETE RESTRICT;


--
-- Name: reservations fk_space; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT fk_space FOREIGN KEY (space_id) REFERENCES public.spaces(id);


--
-- Name: state_changes fk_space; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.state_changes
    ADD CONSTRAINT fk_space FOREIGN KEY (space_id) REFERENCES public.spaces(id);


--
-- Name: sites fk_tenant; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sites
    ADD CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: user_memberships fk_tenant; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.user_memberships
    ADD CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: api_keys fk_tenant; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: user_memberships fk_user; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.user_memberships
    ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: gateways gateways_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.gateways
    ADD CONSTRAINT gateways_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.sites(id);


--
-- Name: gateways gateways_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.gateways
    ADD CONSTRAINT gateways_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: reservations reservations_cancelled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_cancelled_by_fkey FOREIGN KEY (cancelled_by) REFERENCES public.users(id);


--
-- Name: reservations reservations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: reservations reservations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: sensor_devices sensor_devices_assigned_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sensor_devices
    ADD CONSTRAINT sensor_devices_assigned_space_id_fkey FOREIGN KEY (assigned_space_id) REFERENCES public.spaces(id) ON DELETE SET NULL;


--
-- Name: sensor_devices sensor_devices_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sensor_devices
    ADD CONSTRAINT sensor_devices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: sensor_readings sensor_readings_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sensor_readings
    ADD CONSTRAINT sensor_readings_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.sensor_devices(id);


--
-- Name: sensor_readings sensor_readings_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.sensor_readings
    ADD CONSTRAINT sensor_readings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: spaces spaces_display_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.spaces
    ADD CONSTRAINT spaces_display_device_id_fkey FOREIGN KEY (display_device_id) REFERENCES public.display_devices(id);


--
-- Name: spaces spaces_sensor_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: parking_user
--

ALTER TABLE ONLY public.spaces
    ADD CONSTRAINT spaces_sensor_device_id_fkey FOREIGN KEY (sensor_device_id) REFERENCES public.sensor_devices(id);


--
-- Name: display_devices; Type: ROW SECURITY; Schema: public; Owner: parking_user
--

ALTER TABLE public.display_devices ENABLE ROW LEVEL SECURITY;

--
-- Name: gateways; Type: ROW SECURITY; Schema: public; Owner: parking_user
--

ALTER TABLE public.gateways ENABLE ROW LEVEL SECURITY;

--
-- Name: reservations; Type: ROW SECURITY; Schema: public; Owner: parking_user
--

ALTER TABLE public.reservations ENABLE ROW LEVEL SECURITY;

--
-- Name: sensor_devices; Type: ROW SECURITY; Schema: public; Owner: parking_user
--

ALTER TABLE public.sensor_devices ENABLE ROW LEVEL SECURITY;

--
-- Name: spaces; Type: ROW SECURITY; Schema: public; Owner: parking_user
--

ALTER TABLE public.spaces ENABLE ROW LEVEL SECURITY;

--
-- Name: display_devices tenant_isolation_policy; Type: POLICY; Schema: public; Owner: parking_user
--

CREATE POLICY tenant_isolation_policy ON public.display_devices TO parking_user USING (((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid) OR ((current_setting('app.is_platform_admin'::text, true))::boolean = true)));


--
-- Name: gateways tenant_isolation_policy; Type: POLICY; Schema: public; Owner: parking_user
--

CREATE POLICY tenant_isolation_policy ON public.gateways TO parking_user USING (((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid) OR ((current_setting('app.is_platform_admin'::text, true))::boolean = true)));


--
-- Name: reservations tenant_isolation_policy; Type: POLICY; Schema: public; Owner: parking_user
--

CREATE POLICY tenant_isolation_policy ON public.reservations TO parking_user USING (((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid) OR ((current_setting('app.is_platform_admin'::text, true))::boolean = true)));


--
-- Name: sensor_devices tenant_isolation_policy; Type: POLICY; Schema: public; Owner: parking_user
--

CREATE POLICY tenant_isolation_policy ON public.sensor_devices TO parking_user USING (((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid) OR ((current_setting('app.is_platform_admin'::text, true))::boolean = true)));


--
-- Name: spaces tenant_isolation_policy; Type: POLICY; Schema: public; Owner: parking_user
--

CREATE POLICY tenant_isolation_policy ON public.spaces TO parking_user USING (((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid) OR ((current_setting('app.is_platform_admin'::text, true))::boolean = true)));


--
-- PostgreSQL database dump complete
--

\unrestrict H4bPxpZSU3Qo6aZ2SnEJvcDaeY5LCFv2t5Ld5ci1L06WzWc7pUsIQzlKR7egmcz

