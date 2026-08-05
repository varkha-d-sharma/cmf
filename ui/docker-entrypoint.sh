#!/bin/sh

# Create runtime config with environment variables
cat > /usr/share/nginx/html/runtime-config.js <<EOF
window.RUNTIME_CONFIG = {
  REACT_APP_CMF_API_URL: "${REACT_APP_CMF_API_URL:-http://localhost/api}"
};
EOF

echo "Generated runtime configuration"
cat /usr/share/nginx/html/runtime-config.js

# Start nginx
printf '\033[1m============================================================\n  UI Server is started and running\n============================================================\033[0m\n'
exec nginx -g 'daemon off;'
