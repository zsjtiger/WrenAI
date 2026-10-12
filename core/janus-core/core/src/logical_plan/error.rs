use std::{error::Error, fmt::Display};

#[derive(Debug, Clone)]
pub enum JanusError {
    PermissionDenied(String),
}

impl Error for JanusError {}

impl Display for JanusError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            JanusError::PermissionDenied(msg) => write!(f, "Permission Denied: {msg}"),
        }
    }
}
